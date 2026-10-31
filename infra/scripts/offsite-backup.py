#!/usr/bin/env python3
"""Encrypted off-site copy of the newest verified Atlas snapshot (restic). No credentials in arguments or output."""
import argparse
import contextlib
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SNAPSHOT = re.compile(r'atlas-\d{8}T\d{12}Z')
FABRIC_TAG, META_TAG, HOST = 'atlas-fabric', 'atlas-meta', 'atlas'
FABRIC_PATH = 'fabric.tar'  # Stored uncompressed so restic only uploads chunks that changed.
BLOCK = 1024 * 1024


def read_env(path):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep:
            raise ValueError('Linha inválida no arquivo de credenciais.')
        env[key.strip()] = value.strip()
    if not env.get('RESTIC_REPOSITORY'):
        raise ValueError('RESTIC_REPOSITORY ausente no arquivo de credenciais.')
    if env['RESTIC_REPOSITORY'].startswith('s3:') and not (env.get('AWS_ACCESS_KEY_ID') and env.get('AWS_SECRET_ACCESS_KEY')):
        raise ValueError('Chaves de acesso S3/R2 ausentes no arquivo de credenciais.')
    return env


class HashingReader:
    def __init__(self, stream):
        self.stream, self.hash = stream, hashlib.sha256()

    def read(self, size=-1):
        data = self.stream.read(size)
        self.hash.update(data)
        return data


class Offsite:
    def __init__(self, config):
        self.backups = Path(config['backup_path']).resolve()
        self.keep_last = int(config.get('keep_last', 1))
        if self.keep_last < 1:
            raise ValueError('keep_last deve ser positivo.')
        self.env = os.environ.copy()
        self.env.update(read_env(config['env_file']))
        self.env['RESTIC_PASSWORD_FILE'] = config['password_file']
        if config.get('cache_dir'):
            self.env['RESTIC_CACHE_DIR'] = config['cache_dir']

    def restic(self, *args, **kwargs):
        return subprocess.run(['restic', *args], env=self.env, check=True, **kwargs)

    @contextlib.contextmanager
    def locked(self):
        # Same lock as backup-manager.py: the local snapshot cannot be pruned while it is being uploaded.
        with (self.backups / '.backup.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Backup/restauração local em andamento; tente novamente depois.')
            yield

    def newest_local(self):
        snapshots = sorted(p for p in self.backups.iterdir() if p.is_dir() and SNAPSHOT.fullmatch(p.name)
                           and (p / 'manifest.json').is_file())
        if not snapshots:
            raise RuntimeError('Nenhum snapshot local concluído encontrado.')
        return snapshots[-1]

    def remote(self):
        """Snapshot names with both parts uploaded, oldest first, plus every restic snapshot id per name."""
        rows = json.loads(self.restic('snapshots', '--json', '--host', HOST, capture_output=True, text=True).stdout or '[]')
        parts = {}
        for row in rows:
            tags = set(row.get('tags') or [])
            names = [t[5:] for t in tags if t.startswith('snap:')]
            kind = FABRIC_TAG if FABRIC_TAG in tags else META_TAG if META_TAG in tags else None
            if len(names) == 1 and kind:  # restic lists oldest first; retries leave extra ids per part.
                parts.setdefault(names[0], {}).setdefault(kind, []).append(row['id'])
        complete = sorted(n for n, p in parts.items() if FABRIC_TAG in p and META_TAG in p)
        return complete, parts

    def upload(self):
        with self.locked():
            snapshot = self.newest_local()
            name = snapshot.name
            complete, parts = self.remote()
            if name in complete:
                print('Cópia externa já atualizada:', name, flush=True)
                return name
            manifest = json.loads((snapshot / 'manifest.json').read_text())
            if manifest.get('format') != 1 or set(manifest.get('files', {})) != {'database.dump', 'fabric.tar.gz'}:
                raise ValueError('Manifesto local não reconhecido: ' + name)
            tar_sha, tar_size = self.send_fabric(snapshot, name, manifest['files']['fabric.tar.gz'])
            self.send_meta(snapshot, name, manifest, tar_sha, tar_size)
            self.retain()
            print('Cópia externa concluída:', name, flush=True)
            return name

    def send_fabric(self, snapshot, name, expected_gz):
        process = subprocess.Popen(['restic', 'backup', '--quiet', '--host', HOST, '--tag', FABRIC_TAG, '--tag', 'snap:' + name,
                                    '--stdin', '--stdin-filename', FABRIC_PATH], stdin=subprocess.PIPE, env=self.env)
        tar_hash, size = hashlib.sha256(), 0
        try:
            with (snapshot / 'fabric.tar.gz').open('rb') as raw:
                source = HashingReader(raw)
                with gzip.GzipFile(fileobj=source, mode='rb') as stream:
                    for block in iter(lambda: stream.read(BLOCK), b''):
                        tar_hash.update(block)
                        size += len(block)
                        process.stdin.write(block)
                source.read()  # Hash any trailing bytes so the digest covers the whole file.
            if source.hash.hexdigest() != expected_gz:
                raise ValueError('Checksum local inválido: fabric.tar.gz')
        except BaseException:
            process.kill()  # Closing stdin normally would make restic commit a partial snapshot.
            process.wait()
            with contextlib.suppress(OSError):
                process.stdin.close()
            raise
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('restic falhou ao enviar o mundo.')
        return tar_hash.hexdigest(), size

    def send_meta(self, snapshot, name, manifest, tar_sha, tar_size):
        staging = Path(tempfile.mkdtemp(prefix='.offsite-', dir=self.backups))
        try:
            os.link(snapshot / 'database.dump', staging / 'database.dump')
            details = {'format': 1, 'snapshot': name, 'created_at': manifest.get('created_at'),
                       'database': manifest.get('database'), 'files': manifest['files'],
                       'fabric_tar': {'sha256': tar_sha, 'size': tar_size}}
            (staging / 'offsite.json').write_text(json.dumps(details, indent=2) + '\n')
            self.restic('backup', '--quiet', '--host', HOST, '--tag', META_TAG, '--tag', 'snap:' + name, str(staging))
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def retain(self):
        """Keep the newest complete copies only after the new one is fully uploaded."""
        complete, parts = self.remote()
        keep = set(complete[-self.keep_last:])
        stale = [i for n, p in parts.items() for ids in p.values() for i in (ids if n not in keep else ids[:-1])]
        if stale:
            self.restic('forget', '--quiet', '--prune', *stale)
            print('Retenção externa: removidos', len(stale), 'registros antigos.', flush=True)

    def status(self):
        complete, parts = self.remote()
        for name in complete:
            print('Completo:', name)
        for name in sorted(set(parts) - set(complete)):
            print('Incompleto (será removido após o próximo envio):', name)
        if not parts:
            print('Nenhuma cópia externa.')

    def fetch(self, target, name=None):
        """Rebuild a snapshot directory accepted by backup-manager.py verify/restore."""
        target = Path(target).resolve()
        if target.exists() and any(target.iterdir()):
            raise ValueError('Destino precisa estar vazio.')
        complete, parts = self.remote()
        name = name or (complete[-1] if complete else None)
        if name not in complete:
            raise RuntimeError('Cópia externa completa não encontrada.')
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        meta = Path(tempfile.mkdtemp(prefix='.offsite-fetch-', dir=target.parent))
        try:
            self.restic('restore', '--quiet', parts[name][META_TAG][-1], '--target', str(meta))
            details = json.loads(next(meta.rglob('offsite.json')).read_text())
            dump = next(meta.rglob('database.dump'))
            if hashlib.sha256(dump.read_bytes()).hexdigest() != details['files']['database.dump']:
                raise ValueError('Checksum externo inválido: database.dump')
            shutil.move(dump, target / 'database.dump')
            tar_hash, size, gz_hash = hashlib.sha256(), 0, hashlib.sha256()
            with subprocess.Popen(['restic', 'dump', parts[name][FABRIC_TAG][-1], '/' + FABRIC_PATH],
                                  stdout=subprocess.PIPE, env=self.env) as process, \
                    (target / 'fabric.tar.gz').open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=3) as out:
                for block in iter(lambda: process.stdout.read(BLOCK), b''):
                    tar_hash.update(block)
                    size += len(block)
                    out.write(block)
            if process.returncode != 0:
                raise RuntimeError('restic falhou ao baixar o mundo.')
            if tar_hash.hexdigest() != details['fabric_tar']['sha256'] or size != details['fabric_tar']['size']:
                raise ValueError('Checksum externo inválido: fabric.tar')
            with (target / 'fabric.tar.gz').open('rb') as stream:
                for block in iter(lambda: stream.read(BLOCK), b''):
                    gz_hash.update(block)
            manifest = {'format': 1, 'created_at': details['created_at'], 'database': details['database'],
                        'files': {'database.dump': details['files']['database.dump'], 'fabric.tar.gz': gz_hash.hexdigest()}}
            (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        except BaseException:
            shutil.rmtree(target, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(meta, ignore_errors=True)
        print('Cópia externa recuperada em:', target, '(verifique com backup-manager.py verify)')
        return target


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=os.environ.get('ATLAS_OFFSITE_CONFIG', '/etc/atlas/offsite.json'))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('upload')
    commands.add_parser('status')
    fetch = commands.add_parser('fetch'); fetch.add_argument('target'); fetch.add_argument('--snapshot')
    args = parser.parse_args()
    offsite = Offsite(json.loads(Path(args.config).read_text()))
    if args.command == 'upload':
        offsite.upload()
    elif args.command == 'status':
        offsite.status()
    else:
        offsite.fetch(args.target, args.snapshot)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, StopIteration, subprocess.CalledProcessError) as exc:
        print('ERRO:', exc, file=sys.stderr)
        sys.exit(1)
