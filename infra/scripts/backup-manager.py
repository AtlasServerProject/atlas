#!/usr/bin/env python3
"""Offline Atlas snapshots. No credentials in command arguments or manifests."""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile

EXCLUDED = {'.fabric', '.mixin.out', 'logs', 'crash-reports', 'mods-disabled', 'atlas-admin.sock'}
SNAPSHOT = re.compile(r'atlas-\d{8}T\d{12}Z')


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Manager:
    def __init__(self, config):
        self.config = config
        self.source = Path(config['fabric_path']).resolve()
        self.backups = Path(config['backup_path']).resolve()
        self.service = config.get('service', 'atlas.service')
        self.keep_days = int(config.get('retention_days', 30))
        self.keep_min = int(config.get('minimum_copies', 2))
        if self.keep_days < 1 or self.keep_min < 1:
            raise ValueError('Retenção e mínimo de cópias devem ser positivos.')
        if self.backups == self.source or self.source in self.backups.parents:
            raise ValueError('Backups devem ficar fora da pasta Fabric.')
        if not self.source.is_dir() or self.source == Path('/'):
            raise ValueError('Pasta Fabric inválida.')
        self.env = os.environ.copy()
        db = config['postgres']
        self.env.update(PGHOST=str(db['host']), PGPORT=str(db.get('port', 5432)),
                        PGUSER=db['user'], PGDATABASE=db['database'], PGCONNECT_TIMEOUT='15')
        if db.get('passfile'):
            self.env['PGPASSFILE'] = db['passfile']
        self.backups.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def locked(self):
        with (self.backups / '.backup.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Já existe backup/restauração em andamento.')
            yield

    def active(self):
        if not self.service:
            return False  # Explicit offline fixtures / independently stopped installations only.
        state = subprocess.check_output(['systemctl', 'show', self.service, '-p', 'ActiveState', '--value'], text=True).strip()
        if state not in ('active', 'inactive', 'failed'):
            raise RuntimeError('Serviço em transição; tente novamente: ' + state)
        return state == 'active'

    def control(self, operation):
        if self.service:
            command = ['systemctl', '--no-ask-password', operation, self.service]
            if os.geteuid() != 0:
                command = ['sudo', '-n'] + command
            run(command)

    def preflight(self):
        for command in ('pg_dump', 'pg_restore', 'psql'):
            if not shutil.which(command):
                raise RuntimeError('Dependência ausente: ' + command)
        run(['psql', '-X', '-w', '-Atc', 'SELECT 1'], env=self.env, stdout=subprocess.DEVNULL)
        size = sum(p.stat().st_size for p in self.source.rglob('*') if p.is_file() and not p.is_symlink()
                   and not any(part in EXCLUDED for part in p.relative_to(self.source).parts))
        db_bytes = int(subprocess.check_output(['psql', '-X', '-w', '-Atc', 'SELECT pg_database_size(current_database())'], env=self.env, text=True))
        if shutil.disk_usage(self.backups).free < size + db_bytes + 512 * 1024**2:
            raise RuntimeError('Espaço insuficiente: necessário tamanho descomprimido dos arquivos + banco + 512 MiB.')

    def create(self):
        """Caller holds lock and keeps Minecraft stopped throughout this operation."""
        name = 'atlas-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        staging = self.backups / ('.partial-' + name)
        staging.mkdir(mode=0o700)
        try:
            run(['pg_dump', '-w', '--format=custom', '--file', str(staging / 'database.dump')], env=self.env)
            run(['pg_restore', '--list', str(staging / 'database.dump')], stdout=subprocess.DEVNULL)
            def filter_entry(member):
                if not (member.isfile() or member.isdir()):
                    raise RuntimeError('Tipo de arquivo não suportado: ' + member.name)
                return member
            with tarfile.open(staging / 'fabric.tar.gz', 'w:gz', compresslevel=3) as archive:
                for child in sorted(self.source.iterdir()):
                    if child.name not in EXCLUDED:
                        archive.add(child, arcname=child.name, filter=filter_entry)
            files = {name: digest(staging / name) for name in ('database.dump', 'fabric.tar.gz')}
            manifest = {'format': 1, 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                        'database': self.env['PGDATABASE'], 'files': files}
            (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            self.verify(staging)
            final = self.backups / name
            staging.rename(final)
            print('Backup concluído:', final, flush=True)
            return final
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def verify(self, snapshot):
        snapshot = Path(snapshot).resolve()
        manifest = json.loads((snapshot / 'manifest.json').read_text())
        if manifest.get('format') != 1 or set(manifest['files']) != {'database.dump', 'fabric.tar.gz'}:
            raise ValueError('Manifesto não reconhecido.')
        for name, expected in manifest['files'].items():
            if digest(snapshot / name) != expected:
                raise ValueError('Checksum inválido: ' + name)
        run(['pg_restore', '--list', str(snapshot / 'database.dump')], stdout=subprocess.DEVNULL)
        with tarfile.open(snapshot / 'fabric.tar.gz', 'r:gz') as archive:
            for member in archive:
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise ValueError('Entrada insegura no arquivo: ' + member.name)
        return manifest

    def prune(self):
        snapshots = sorted((p for p in self.backups.iterdir() if p.is_dir() and SNAPSHOT.fullmatch(p.name)), reverse=True)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=self.keep_days)
        for snapshot in snapshots[self.keep_min:]:
            try:
                manifest = json.loads((snapshot / 'manifest.json').read_text())
                if manifest.get('format') == 1 and dt.datetime.fromisoformat(manifest['created_at']) < cutoff:
                    shutil.rmtree(snapshot)
                    print('Retenção: removido', snapshot.name)
            except (OSError, ValueError, KeyError):
                print('Retenção: ignorado manifesto inválido:', snapshot.name, file=sys.stderr)

    def backup(self):
        with self.locked():
            self.preflight()
            was_active = self.active()
            try:
                if was_active:
                    self.control('stop')
                if self.active():
                    raise RuntimeError('Servidor ainda ativo; backup cancelado.')
                snapshot = self.create()
            finally:
                if was_active:
                    self.control('start')
            self.prune()  # Only after a new complete snapshot and successful restart.
            return snapshot

    def restore(self, snapshot, target=None, database=None):
        snapshot = Path(snapshot).resolve()
        with self.locked():
            manifest = self.verify(snapshot)
            isolated = target is not None
            if isolated:
                target = Path(target).resolve()
                if target == self.source or self.source in target.parents or target in self.source.parents:
                    raise ValueError('Destino isolado não pode sobrepor produção.')
                if target == self.backups or self.backups in target.parents or target in self.backups.parents:
                    raise ValueError('Destino isolado não pode sobrepor backups.')
                if not database or database == self.env['PGDATABASE']:
                    raise ValueError('Use banco de teste diferente da produção.')
                if target.exists() and any(target.iterdir()):
                    raise ValueError('Destino de teste precisa estar vazio.')
            else:
                target = self.source
                database = self.env['PGDATABASE']
                if manifest['database'] != database:
                    raise ValueError('Backup pertence a outro banco.')
                self.preflight()
            restore_env = dict(self.env, PGDATABASE=database)
            # Target database must exist. Isolated databases must be empty.
            table_count = int(subprocess.check_output(['psql', '-X', '-w', '-Atc',
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f')"], env=restore_env, text=True))
            if isolated and table_count:
                raise ValueError('Banco de teste precisa estar vazio.')
            target.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix='.atlas-restore-', dir=target.parent))
            stopped = False
            try:
                with tarfile.open(snapshot / 'fabric.tar.gz', 'r:gz') as archive:
                    needed = sum(m.size for m in archive.getmembers())
                    if shutil.disk_usage(staging).free < needed + 512 * 1024**2:
                        raise RuntimeError('Espaço insuficiente para extração.')
                    archive.extractall(staging, filter='data')
                if not isolated:
                    self.control('stop')
                    stopped = True
                    if self.active():
                        raise RuntimeError('Servidor ainda ativo; restauração cancelada.')
                    safety = self.create()
                    print('Backup de segurança pré-restauração:', safety, flush=True)
                    stat = self.source.stat()
                    for path in [staging, *staging.rglob('*')]:
                        os.chown(path, stat.st_uid, stat.st_gid)
                # Single PostgreSQL transaction: an SQL failure leaves the original DB intact.
                run(['pg_restore', '-w', '--exit-on-error', '--single-transaction', '--clean', '--if-exists',
                     '--no-owner', '--no-privileges', '--dbname', database, str(snapshot / 'database.dump')], env=restore_env)
                previous = target.with_name(target.name + '.pre-restore-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                if target.exists():
                    target.rename(previous)
                staging.rename(target)
                if not isolated:
                    self.control('start')
                print('Restauração concluída:', target, 'banco:', database)
                print('Diretório anterior preservado em:', previous)
            except BaseException:
                if stopped:
                    print('Falha: servidor mantido parado. Consulte o backup pré-restauração antes de reiniciar.', file=sys.stderr)
                raise
            finally:
                if staging.exists():
                    shutil.rmtree(staging)


def main():
    os.umask(0o077)
    def interrupted(signum, frame):
        raise RuntimeError(f"Operação interrompida pelo sinal {signum}.")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=os.environ.get('ATLAS_BACKUP_CONFIG', '/etc/atlas/backup.json'))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('backup')
    verify = commands.add_parser('verify'); verify.add_argument('snapshot')
    restore = commands.add_parser('restore'); restore.add_argument('snapshot')
    restore.add_argument('--confirm', action='store_true', help='Confirma substituição dos dados de destino')
    restore.add_argument('--target', help='Diretório vazio para teste isolado')
    restore.add_argument('--database', help='Banco vazio já criado para teste isolado')
    args = parser.parse_args()
    manager = Manager(json.loads(Path(args.config).read_text()))
    if args.command == 'backup':
        manager.backup()
    elif args.command == 'verify':
        manager.verify(args.snapshot); print('Integridade aprovada.')
    else:
        if not args.confirm:
            parser.error('Restauração exige --confirm; leia o guia de backup antes de continuar.')
        if bool(args.target) != bool(args.database):
            parser.error('--target e --database devem ser usados juntos.')
        manager.restore(args.snapshot, args.target, args.database)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('ERRO:', exc, file=sys.stderr)
        sys.exit(1)
