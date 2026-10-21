#!/usr/bin/env python3
"""Provision a separate test instance. Never copy production gameplay data."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[2]


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def private_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(contents)
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/opt/atlas/server/fabric"))
    parser.add_argument("--root", type=Path, default=Path.home() / ".local/share/atlas-dev")
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--public-host", default="", help="Empty uses the hostname from the client's handshake")
    args = parser.parse_args()
    source, root, jar = args.source.resolve(), args.root.resolve(), args.jar.resolve()
    if root == source or root.is_relative_to(source) or source.is_relative_to(root):
        raise SystemExit("Production and test directories must be separate.")
    if not jar.is_file() or not jar.name.startswith("atlas-core-") or "sources" in jar.name:
        raise SystemExit("A built atlas-core runtime JAR is required.")
    if any(char in args.public_host for char in "\n\r=\x00"):
        raise SystemExit("Invalid public hostname.")
    marker = root / ".atlas-dev-instance"
    if root.exists() and any(root.iterdir()) and not marker.exists():
        raise SystemExit("Refusing to overwrite an unmanaged directory.")
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    marker.write_text("Atlas isolated development instance v1\n")
    server = root / "fabric"
    server.mkdir(exist_ok=True)
    (root / "run").mkdir(exist_ok=True)
    pg_bin = Path("/usr/lib/postgresql/18/bin")
    if not (pg_bin / "initdb").is_file():
        raise SystemExit("PostgreSQL 18 binaries are required.")
    credentials = root / "database-secrets"
    if credentials.exists():
        admin_password, app_password = credentials.read_text().splitlines()
    else:
        admin_password, app_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        private_write(credentials, f"{admin_password}\n{app_password}\n")
    key_path = root / "broker.key"
    if not key_path.exists():
        private_write(key_path, secrets.token_urlsafe(32))
    key = key_path.read_text().strip()
    pgdata = root / "postgres"
    if not (pgdata / "PG_VERSION").exists():
        with tempfile.NamedTemporaryFile(mode="w", dir=root) as password_file:
            password_file.write(admin_password)
            password_file.flush()
            run([str(pg_bin / "initdb"), "-D", str(pgdata), "--username=atlas_dev_admin",
                 "--auth-local=trust", "--auth-host=scram-sha-256", "--pwfile", password_file.name], stdout=subprocess.DEVNULL)
        with (pgdata / "postgresql.conf").open("a") as config:
            config.write(f"\nlisten_addresses='127.0.0.1'\nport=25432\nunix_socket_directories='{root / 'run'}'\nshared_buffers='32MB'\nmax_connections=20\n")
    units = Path.home() / ".config/systemd/user"
    units.mkdir(parents=True, exist_ok=True)
    (units / "atlas-dev-postgres.service").write_text(f"""[Unit]
Description=Atlas test PostgreSQL (isolated cluster)
StartLimitIntervalSec=300
StartLimitBurst=3
[Service]
ExecStart={pg_bin}/postgres -D {pgdata}
Restart=on-failure
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=60
UMask=0077
[Install]
WantedBy=default.target
""")
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", "atlas-dev-postgres.service"])
    import time
    for _ in range(30):
        ready = subprocess.run([str(pg_bin / "pg_isready"), "-h", str(root / "run"), "-p", "25432"], capture_output=True)
        if ready.returncode == 0:
            break
        time.sleep(0.2)
    else:
        raise SystemExit("Private PostgreSQL did not become ready.")
    psql = [str(pg_bin / "psql"), "-X", "-v", "ON_ERROR_STOP=1", "-h", str(root / "run"), "-p", "25432", "-U", "atlas_dev_admin"]
    databases = subprocess.check_output(psql + ["-d", "postgres", "-Atc", "SELECT datname FROM pg_database"], text=True).splitlines()
    if "atlas_dev" not in databases:
        # Passwords are generated locally; SQL is sent on stdin and never printed.
        bootstrap = f"CREATE ROLE atlas_dev LOGIN PASSWORD '{app_password}';\nCREATE ROLE atlas_app NOLOGIN;\nCREATE DATABASE atlas_dev;\n"
        result = subprocess.run(psql + ["-d", "postgres"], input=bootstrap, text=True, capture_output=True)
        if result.returncode != 0:
            raise SystemExit("Failed to initialize private database roles.")
    sql_command = psql + ["-d", "atlas_dev"]
    run(sql_command, input="CREATE TABLE IF NOT EXISTS schema_migrations(filename TEXT PRIMARY KEY, executed_at TIMESTAMPTZ DEFAULT NOW());", text=True, stdout=subprocess.DEVNULL)
    applied = set(subprocess.check_output(sql_command + ["-Atc", "SELECT filename FROM schema_migrations"], text=True).splitlines())
    for migration in sorted((PROJECT / "database/migrations").glob("*.sql")):
        if migration.name in applied:
            continue
        sql = "BEGIN;\n" + migration.read_text() + f"\nINSERT INTO schema_migrations(filename) VALUES ('{migration.name}');\nCOMMIT;"
        run(sql_command, input=sql, text=True, stdout=subprocess.DEVNULL)
    seed = """
INSERT INTO ranks(identifier,display_name,prefix,priority,color,is_staff)
VALUES ('owner','Dono','[DONO]',100,'dark_red',true),('admin','ADM','[ADM]',90,'red',true),('member','Treinador','',0,'gray',false)
ON CONFLICT(identifier) DO NOTHING;
INSERT INTO rank_permissions(rank_id,permission) SELECT id,'*' FROM ranks WHERE identifier IN ('owner','admin') ON CONFLICT DO NOTHING;
GRANT CONNECT ON DATABASE atlas_dev TO atlas_dev;
GRANT USAGE ON SCHEMA public TO atlas_dev;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO atlas_dev;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO atlas_dev;
"""
    run(sql_command, input=seed, text=True, stdout=subprocess.DEVNULL)
    # Runtime code only. No production config, world, playerdata, accounts, wallets or Pokémon.
    for filename in ("fabric-server-launch.jar", "fabric-server-launcher.properties", "server.jar"):
        shutil.copy2(source / filename, server / filename)
    for directory in ("libraries", "versions", "lib"):
        if (source / directory).exists():
            shutil.copytree(source / directory, server / directory, dirs_exist_ok=True)
    mods = server / "mods"
    mods.mkdir(exist_ok=True)
    for mod in (source / "mods").glob("*.jar"):
        if not mod.name.startswith("atlas-core-"):
            shutil.copy2(mod, mods / mod.name)
    for old in mods.glob("atlas-core-*.jar"):
        if old.name != jar.name:
            backup = root / "jar-backups"
            backup.mkdir(exist_ok=True)
            shutil.move(str(old), str(backup / old.name))
    shutil.copy2(jar, mods / jar.name)
    world = server / "world"
    world.mkdir(exist_ok=True)
    shutil.copytree(PROJECT / "infra/templates/lobbies/atlas-lobbies", world / "datapacks/atlas-lobbies", dirs_exist_ok=True)
    (server / "eula.txt").write_text((source / "eula.txt").read_text())
    (server / "server.properties").write_text("""server-port=25566
server-ip=
online-mode=false
accepts-transfers=true
enforce-secure-profile=false
level-name=world
level-type=minecraft:flat
generator-settings={"biome":"minecraft:plains","layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},{"block":"minecraft:grass_block","height":1}],"features":false,"lakes":false,"structure_overrides":[]}
generate-structures=false
gamemode=survival
motd=Atlas - Lobby de Testes (Dono/ADM)
max-players=10
view-distance=5
simulation-distance=3
enable-rcon=false
enable-query=false
spawn-protection=0
sync-chunk-writes=true
""")
    config = server / "config"
    config.mkdir(exist_ok=True)
    for forbidden in ("atlas-site.properties", "atlas-vip.properties"):
        if (config / forbidden).exists():
            raise SystemExit("Production commercial configuration must not be present in the test instance.")
    private_write(config / "atlas-database.properties", f"host=127.0.0.1\nport=25432\ndatabase=atlas_dev\nuser=atlas_dev\npassword={app_password}\n")
    shared = f"broker-key={key}\nbroker-port=25567\ndev-port=25566\nmain-port=25565\npublic-host={args.public_host}\nuser-runtime-dir=/run/user/{os.getuid()}\n"
    private_write(config / "atlas-dev.properties", "mode=development\n" + shared)
    private_write(source / "config/atlas-dev.properties", "mode=primary\n" + shared)
    (units / "atlas-dev.service").write_text(f"""[Unit]
Description=Atlas isolated test lobby
Requires=atlas-dev-postgres.service
After=atlas-dev-postgres.service
StartLimitIntervalSec=300
StartLimitBurst=3
[Service]
WorkingDirectory={server}
ExecStart=/usr/bin/java -Xms512M -Xmx1536M -jar fabric-server-launch.jar nogui
ExecStop=/usr/bin/python3 {PROJECT}/infra/scripts/stop-dev-lobby.py --pid $MAINPID --socket {server}/atlas-admin.sock
Restart=on-failure
RestartSec=10
TimeoutStopSec=120
KillSignal=SIGINT
SuccessExitStatus=0 130 143
UMask=0077
[Install]
WantedBy=default.target
""")
    run(["systemctl", "--user", "daemon-reload"])
    print("Prepared private PostgreSQL, test world/mods and user service. No production data copied.")
    print("Start the test instance with: systemctl --user start atlas-dev.service (production also starts it on demand)")


if __name__ == "__main__":
    main()
