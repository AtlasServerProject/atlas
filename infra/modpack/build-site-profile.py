#!/usr/bin/env python3
"""Build a small import profile matching the launcher's current signed catalogue.
Official CurseForge files remain references; bundled mods retain credits/licenses.
"""
import base64, hashlib, io, json, pathlib, struct, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
release = json.loads(base64.b64decode(json.loads((ROOT/'atlas-web/public/launcher/modpack.json').read_text())['payload']))
source = pathlib.Path('/home/somente/downloads/MODS/Atlas-Cobblemon-1.0.1-CurseForge.zip')
with zipfile.ZipFile(source) as z:
    entries = {n:z.read(n) for n in z.namelist()}
manifest = json.loads(entries['manifest.json'])
original_refs = {(f['projectID'],f['fileID']) for f in manifest['files']}
refs, verified = [], []
for f in release['files']:
    name = pathlib.PurePosixPath(f['path']).name
    if not f['path'].startswith('mods/'):
        raise ValueError('Unexpected non-mod catalogue entry')
    if f['url'].startswith('atlas-bundled:///'):
        data = (ROOT/'atlas-launcher/apps/desktop/resources/bundled'/name).read_bytes()
        entries['overrides/mods/'+name] = data
        with zipfile.ZipFile(io.BytesIO(data)) as jar:
            for n in jar.namelist():
                if '/' not in n.strip('/') and any(w in n.lower() for w in ('license','notice','copying')):
                    entries['overrides/atlas-info/licenses/'+name+'/'+n] = jar.read(n)
    else:
        parts = pathlib.PurePosixPath(f['url'].split('?',1)[0]).parts
        row = next((r for r in manifest['files'] if '/files/' in f['url'] and str(r['fileID']) == parts[-3]+parts[-2].zfill(3)), None)
        if row is not None:
            # The file ID in the official download URL must match the pinned import entry.
            parts = pathlib.PurePosixPath(f['url'].split('?',1)[0]).parts
            assert str(row['fileID']) == parts[-3]+parts[-2].zfill(3), name
            refs.append({'projectID':row['projectID'],'fileID':row['fileID'],'required':True})
            # Confirm the original archive and current launcher catalogue describe identical bytes.
            with zipfile.ZipFile('/home/somente/downloads/MODS/mods.zip') as z:
                matches = [n for n in z.namelist() if pathlib.PurePosixPath(n).name == name]
                assert len(matches)==1, name
                data = z.read(matches[0])
        else:
            data = entries['overrides/mods/'+name]
    assert len(data)==f['size'] and hashlib.sha256(data).hexdigest()==f['sha256'],name
    verified.append({'file':name,'sha256':f['sha256']})
assert {(f['projectID'],f['fileID']) for f in refs}==original_refs
assert len(refs)+len([n for n in entries if n.startswith('overrides/mods/') and n.endswith('.jar')])==len(verified)==58
manifest.update(version=release['version'],files=sorted(refs,key=lambda f:f['projectID']))
entries['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
# Java's uncompressed NBT server list; never include player/account data.
def string(s):
    b=s.encode();return struct.pack('>H',len(b))+b
fields=b'\x08'+string('name')+string('Atlas Cobblemon')+b'\x08'+string('ip')+string('stapling-gpo.tun.ply.gg')+b'\x00'
entries['overrides/servers.dat']=b'\x0a\x00\x00\x09'+string('servers')+b'\x0a'+struct.pack('>i',1)+fields+b'\x00'
readme=f'''ATLAS COBBLEMON {release['version']} — PERFIL IMPORTÁVEL
Minecraft Java 1.21.1 | Fabric Loader 0.18.0 | Java 21 | 58 mods

1. Crie uma instância separada importando este ZIP no seu launcher compatível
   com manifest.json do CurseForge (por exemplo, Prism Launcher: Adicionar
   instância > Importar). Mantenha o ZIP inteiro durante a importação.
2. O launcher baixa os mods oficiais referenciados no manifest.json e copia
   os mods complementares de overrides/mods. Não copie este ZIP na pasta mods.
3. Selecione Java 21. Recomendamos 4 GB de RAM disponíveis para o jogo;
   ajuste ao seu computador, sem reservar toda a memória para o Minecraft.
4. Abra a instância e conecte a stapling-gpo.tun.ply.gg.
   Aceite o pacote de recursos oferecido pelo servidor.

Este download é uma alternativa ao Atlas Launcher. Não inclui Minecraft,
Java ou conta. O seu launcher precisa preparar o jogo e o Fabric.
Não atualiza automaticamente: para uma nova versão, importe o novo pacote
em outra instância e preserve seus mundos/configurações pessoais.

As versões e os hashes dos 58 mods correspondem ao catálogo atual do Atlas
Launcher. Battle Positions e Atlas Interface estão incluídos.
Perfil distribuído pelo site Atlas; não representa aprovação da moderação
CurseForge. Créditos de terceiros preservados em atlas-info/CREDITS.md.
Sem mundos do servidor, senhas, tokens ou arquivos administrativos.
Site: https://www.atlascobblemon.com.br
'''
entries['overrides/atlas-info/README.txt']=readme.encode()
entries['overrides/atlas-info/CHANGELOG.txt']=f'''Atlas Cobblemon {release['version']}
- Sincroniza os 58 mods com o catálogo do Atlas Launcher.
- Inclui Battle Positions e Atlas Interface 1.1.3.
- Atualiza o endereço do servidor e as instruções de importação.
'''.encode()
entries['overrides/atlas-info/CREDITS.md']+=b'\n## Additional site profile components\n\nCobblemon Battle Positions: Ramen, MIT. Original license bundled in licenses/.\nAtlas Interface 1.1.3: Atlas Cobblemon.\n'
entries['overrides/atlas-info/catalogue.json']=(json.dumps({'version':release['version'],'mods':verified},indent=2)+'\n').encode()
entries['modlist.html']=entries['modlist.html'].replace(b'Atlas Cobblemon 1.0.1',('Atlas Cobblemon '+release['version']).encode())
out=ROOT/'atlas-web/public/downloads'/f"Atlas-Cobblemon-{release['version']}-Importar.zip"
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for n,data in sorted(entries.items()):
        assert not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts
        z.writestr(n,data)
with zipfile.ZipFile(out) as z: assert z.testzip() is None
assert out.stat().st_size<25*1024*1024
out.with_suffix('.zip.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print(f'{out}: {out.stat().st_size} bytes, {len(verified)} verified mods')
