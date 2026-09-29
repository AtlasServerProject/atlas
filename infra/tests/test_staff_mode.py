#!/usr/bin/env python3
"""Exercise production repository/policy with Java 21 and disposable PostgreSQL."""
from pathlib import Path
import os
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PG = Path(subprocess.check_output(['pg_config', '--bindir'], text=True).strip())
DRIVERS = [p for p in (Path.home() / '.gradle/caches/modules-2/files-2.1/org.postgresql/postgresql').rglob('postgresql-*.jar')
           if not p.name.endswith(('-javadoc.jar', '-sources.jar'))]
if not DRIVERS:
    raise SystemExit('Execute o build do atlas-core antes deste teste para obter o JDBC.')
with tempfile.TemporaryDirectory(prefix='atlas-staff-mode-') as directory:
    temp = Path(directory)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    subprocess.run([str(PG/'initdb'), '-D', str(temp/'pg'), '-A', 'trust', '-U', 'postgres', '--no-locale'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(PG/'pg_ctl'), '-D', str(temp/'pg'), '-l', str(temp/'postgres.log'), '-o',
                    f"-k {temp} -p {port} -c listen_addresses=127.0.0.1", '-w', 'start'], check=True, stdout=subprocess.DEVNULL)
    try:
        env = dict(os.environ, PGHOST=str(temp), PGPORT=str(port), PGUSER='postgres', PGDATABASE='postgres',
                   ATLAS_TEST_JDBC=f'jdbc:postgresql://127.0.0.1:{port}/postgres')
        for _ in range(2):
            subprocess.run(['psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-f', str(ROOT/'database/migrations/031_staff_mode_sessions.sql')], env=env, check=True, stdout=subprocess.DEVNULL)
        sources = ROOT/'atlas-core/src/main/java/io/atlas/modules/moderation'
        subprocess.run(['javac', '--release', '21', '-encoding', 'UTF-8', '-d', str(temp/'classes'),
                        str(sources/'model/StaffModeSession.java'), str(sources/'repository/StaffModeRepository.java'),
                        str(sources/'service/StaffModePolicy.java'), str(ROOT/'infra/tests/java/StaffModeRepositoryTest.java')], check=True)
        subprocess.run(['java', '-cp', os.pathsep.join([str(temp/'classes'), str(DRIVERS[0])]), 'StaffModeRepositoryTest'], env=env, check=True)
    finally:
        subprocess.run([str(PG/'pg_ctl'), '-D', str(temp/'pg'), '-m', 'immediate', '-w', 'stop'], check=True, stdout=subprocess.DEVNULL)
