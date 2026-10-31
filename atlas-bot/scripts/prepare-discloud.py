#!/usr/bin/env python3
"""Build an allowlisted public ZIP, or a private CLI staging directory with credentials."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '.runtime' / 'discloud'

def files():
    package=json.loads((ROOT/'package.json').read_text())
    cloud={key:package[key] for key in ('name','version','private','type','engines')}
    cloud['scripts']={'start':'node --max-old-space-size=48 --env-file-if-exists=.env build/atlas-bot.js'}
    cloud['dependencies']={}
    yield 'package.json', json.dumps(cloud,indent=2).encode()
    yield 'package-lock.json', json.dumps({'name':cloud['name'],'version':cloud['version'],'lockfileVersion':3,'requires':True,'packages':{'':{'name':cloud['name'],'version':cloud['version'],'engines':cloud['engines']}}}).encode()
    yield '.env.example', (ROOT/'.env.example').read_bytes()
    yield 'build/atlas-bot.js', (ROOT/'.runtime/cloud-build/atlas-bot.js').read_bytes()
    yield 'discloud.config', (ROOT/'deploy/discloud.config').read_bytes()

def parse_env(path):
    result = subprocess.run(['node', '--input-type=module', '-e',
        "import {readFileSync} from 'node:fs';import {parseEnv} from 'node:util';process.stdout.write(JSON.stringify(parseEnv(readFileSync(process.argv[1],'utf8'))));",
        str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def prepare_private(source):
    env = parse_env(source)
    for key in ('DISCORD_TOKEN','DISCORD_APPLICATION_ID','DISCORD_GUILD_ID'):
        if not env.get(key):
            raise ValueError('Configuração incompleta: '+key)
    old_state = Path(env.get('ATLAS_NEWS_STATE_FILE', '.runtime/news-state.json'))
    if not old_state.is_absolute(): old_state = ROOT / old_state
    address = env.get('MINECRAFT_ADDRESS', '').strip()
    if not address:
        guide = ROOT.parent/'atlas-web/src/app/pages/how-to-play/how-to-play-page.component.html'
        matches = re.findall(r'class="server-address"[^>]*>.*?<code>([^<]+)</code>', guide.read_text(), re.DOTALL) if guide.exists() else []
        if len(matches)==1: address=matches[0].strip()
    env['MINECRAFT_ADDRESS']=address
    if not address or '/' in address:
        raise ValueError('Configure o endereço público Minecraft antes de migrar.')
    if address.count(':') == 1:
        host, port = address.rsplit(':',1)
        if not port.isdigit(): raise ValueError('Porta pública inválida')
    else:
        host, port = address, '25565'
    if host in ('localhost','127.0.0.1','0.0.0.0'):
        raise ValueError('O bot na nuvem precisa do endereço público Minecraft.')
    env.update(MINECRAFT_STATUS_HOST=host,MINECRAFT_STATUS_PORT=port,
               ATLAS_BRIDGE_SECRET='',ATLAS_NEWS_STATE_FILE='.runtime/news-state.json')
    # Only explicitly supported settings are carried over; never copy the API key.
    allowed = set(parse_env(ROOT/'.env.example'))
    env = {key:value for key,value in env.items() if key in allowed}
    os.umask(0o077)
    if STAGE.exists():
        if STAGE.is_symlink(): raise ValueError('Staging não pode ser link simbólico')
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True,exist_ok=True); STAGE.chmod(0o700)
    for name,data in files():
        target=STAGE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    # Preserve cloud app identity across future commits.
    local_config=STAGE/'discloud.config'
    identity=ROOT/'.runtime'/'discloud-app-id'
    if identity.exists():
        app=identity.read_text().strip()
        if not app.isdigit(): raise ValueError('ID da aplicação inválido')
        with local_config.open('a') as out: out.write('ID='+app+'\n')
    # dotenv's quoted values support escaped newlines; reject raw double quotes.
    if any('"' in str(v) or '\r' in str(v) or '\n' in str(v) for v in env.values()):
        raise ValueError('Configuração contém valor não suportado para exportação dotenv.')
    target=STAGE/'.env';target.write_text(''.join(f'{key}="{value}"\n' for key,value in env.items()));target.chmod(0o600)
    if old_state.is_file():
        target=STAGE/'.runtime/news-state.json';target.parent.mkdir(exist_ok=True);shutil.copy2(old_state,target);target.chmod(0o600)
    (STAGE/'.discloudignore').write_text('node_modules\n.git\n*.zip\n*.log\n')
    print('Staging privado preparado:', STAGE)
    print('Consulta Minecraft configurada para o endereço público; bridge local desabilitada.')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--private',action='store_true')
    parser.add_argument('--env-file',type=Path,default=Path.home()/'.config/atlas/discord-bot.env')
    parser.add_argument('--output',type=Path,default=Path.home()/'downloads/Atlas-Bot-Discloud.zip')
    args=parser.parse_args()
    subprocess.run(['npm','run','build:cloud'],cwd=ROOT,check=True)
    if args.private: prepare_private(args.env_file); return
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files(): archive.writestr(name,data)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert '.env' not in archive.namelist()
    print('ZIP sem credenciais preparado:',args.output)
if __name__=='__main__': main()
