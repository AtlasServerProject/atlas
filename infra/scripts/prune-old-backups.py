#!/usr/bin/env python3
"""Remove old Atlas snapshots only after verifying the newest recovery copies."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil

SNAPSHOT = re.compile(r'atlas-\d{8}T\d{12}Z')


def prune(manager, keep=2, apply=False):
    if keep < 2:
        raise ValueError('Preserve pelo menos duas cópias completas.')
    snapshots = sorted((p for p in manager.backups.iterdir()
                        if p.is_dir() and not p.is_symlink() and SNAPSHOT.fullmatch(p.name)),
                       key=lambda p: p.name, reverse=True)
    verified = []
    for path in snapshots:
        try:
            manager.verify(path)
        except Exception as error:
            print(f'Preservado para inspeção: {path.name} ({type(error).__name__})', flush=True)
            continue
        verified.append(path)
        if len(verified) == keep:
            break
    if len(verified) < keep:
        raise RuntimeError('Não há duas cópias completas verificáveis; nada foi removido.')
    cutoff = verified[-1].name
    candidates = [p for p in snapshots if p.name < cutoff]
    for path in verified:
        print('Cópia verificada e preservada:', path.name, flush=True)
    for path in candidates:
        print(('Removendo: ' if apply else 'Simulação — removeria: ') + path.name, flush=True)
        if apply:
            shutil.rmtree(path)
    return candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('/etc/atlas/backup.json'))
    parser.add_argument('--apply', action='store_true', help='Executar a remoção; padrão é simulação.')
    args = parser.parse_args()
    module_path = Path(__file__).with_name('backup-manager.py')
    spec = importlib.util.spec_from_file_location('atlas_backup_manager', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager = module.Manager(json.loads(args.config.read_text()))
    expected = Path('/opt/atlas/server/backups/snapshots')
    if manager.backups != expected:
        raise RuntimeError('Destino inesperado; este utilitário só limpa snapshots do Atlas.')
    with manager.locked():
        before = shutil.disk_usage(manager.backups).free
        prune(manager, keep=max(2, manager.keep_min), apply=args.apply)
        if args.apply:
            print(f'Espaço liberado: {(shutil.disk_usage(manager.backups).free - before) / 2**30:.2f} GiB')


if __name__ == '__main__':
    main()
