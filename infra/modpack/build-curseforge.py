#!/usr/bin/env python3
"""Build a CurseForge import ZIP from a verified local archive and catalogue snapshots.
Never runs mod code, downloads executables or includes operator/server configuration.
"""
import argparse,collections,hashlib,html,io,json,pathlib,struct,zipfile

def nbt_string(value):
 data=value.encode('utf-8');return struct.pack('>H',len(data))+data

def server_list():
 # Uncompressed Java NBT: root compound -> servers list -> one compound.
 fields=b'\x08'+nbt_string('name')+nbt_string('Atlas Cobblemon')+b'\x08'+nbt_string('ip')+nbt_string('jogar.atlascobblemon.com.br')+b'\x01'+nbt_string('acceptTextures')+b'\x01\x00'
 return b'\x0a\x00\x00\x09'+nbt_string('servers')+b'\x0a'+struct.pack('>i',1)+fields+b'\x00'

def authors(metadata):
 return ', '.join(a if isinstance(a,str) else a.get('name','Unknown author') for a in metadata.get('authors',[]))

def build(source,work,output):
 rows=json.loads((work/'inventory.json').read_text());files={f['id']:f for f in json.loads((work/'cf-files-current.json').read_text())['data']};projects={p['id']:p for p in json.loads((work/'cf-projects.json').read_text())['data']};fingerprints={m['file']['fileFingerprint']:m['file']['id'] for m in json.loads((work/'fingerprints.json').read_text())['data']['exactMatches']};external={r['file']:r for r in json.loads((work/'noncf.json').read_text())}
 approvals='\n'.join(p.read_text().lower() for p in work.glob('approved-*.csv'))
 excluded={'cobblemonbattlepositions':'Official supplied binary not resolved on CurseForge/Modrinth and no entry found on the approved non-CurseForge list. Retained in the original source archive only.'}
 approved_names={'cobblemon-additions':'cobblemon additions','cobbreeding':'cobbreeding','tmcraft':'tmcraft'}
 manifest={'minecraft':{'version':'1.21.1','modLoaders':[{'id':'fabric-0.18.0','primary':True}]},'manifestType':'minecraftModpack','manifestVersion':1,'name':'Atlas Cobblemon','version':'1.0.1','author':'Atlas Cobblemon','files':[],'overrides':'overrides'}
 entries={};inventory=[];links=[];excluded_files=[];provided={'minecraft','java','fabricloader','mixinextras'}
 # MixinExtras is bundled by Fabric Loader, not a separate mod to install.
 def add_metadata(data):
  with zipfile.ZipFile(io.BytesIO(data)) as j:
   d=json.loads(j.read('fabric.mod.json'),strict=False);provided.add(d['id']);provided.update(d.get('provides',[]))
   for nested in d.get('jars',[]):add_metadata(j.read(nested['file']))
 with zipfile.ZipFile(source) as archive:
  if archive.testzip() is not None:raise ValueError('Source ZIP CRC check failed')
  for row in rows:
   if row['id'] in excluded:excluded_files.append({'file':row['name'],'reason':excluded[row['id']]});continue
   data=archive.read(row['path']);assert hashlib.sha1(data).hexdigest()==row['sha1'],row['name'];add_metadata(data)
   item={'file':row['name'],'id':row['id'],'version':str(row['metadata']['version']),'sha1':row['sha1'],'authors':authors(row['metadata'])}
   if row['fingerprint'] in fingerprints:
    f=files[fingerprints[row['fingerprint']]];assert f['isAvailable'],row['name'];assert any(h['algo']==1 and h['value'].lower()==row['sha1'] for h in f['hashes']),row['name'];project=projects[f['modId']]
    assert 'Fabric' in f['gameVersions'],row['name']
    manifest['files'].append({'projectID':f['modId'],'fileID':f['id'],'required':True});item.update(projectID=f['modId'],fileID=f['id'],source=project['links']['websiteUrl'])
   else:
    assert row['id'] in approved_names and approved_names[row['id']] in approvals,row['name']
    info=external[row['name']];file=next(f for f in info['version']['files'] if f['hashes']['sha1']==row['sha1']);assert hashlib.sha512(data).hexdigest()==file['hashes']['sha512'];entries['overrides/mods/'+row['name']]=data
    item.update(source='https://modrinth.com/mod/'+info['project']['slug']+'/version/'+info['version']['id'],license=row['metadata'].get('license'),distribution='CurseForge approved non-CurseForge list; official binary hash verified')
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
     for name in jar.namelist():
      if '/' not in name.strip('/') and any(word in name.lower() for word in ('license','copying','notice')):entries['overrides/atlas-info/licenses/'+row['id']+'/'+pathlib.Path(name).name]=jar.read(name)
   inventory.append(item);links.append((row['metadata'].get('name',row['id']),item['source']))
  missing=[(r['id'],dep) for r in rows if r['id'] not in excluded for dep in r['metadata'].get('depends',{}) if dep not in provided]
  if missing:raise ValueError('Missing declared dependency IDs: '+repr(missing))
 manifest['files'].sort(key=lambda f:f['projectID'])
 credits=['# Atlas Cobblemon — Credits / Créditos','', 'Minecraft 1.21.1 · Fabric Loader 0.18.0 · Java 21','', 'Mods remain licensed by their respective authors. Atlas ownership does not override third-party licenses.','', '## Approved external mods / Mods externos aprovados','', 'Checked on 25 October 2026 against the list linked by CurseForge:','https://docs.google.com/spreadsheets/d/176Wv-PZUo9hFxy6oC6N8tWdquBLPRtSuLbNK-r0_byM/edit','']
 for item in inventory:
  if item.get('distribution'):credits+=['### '+item['id'], 'Authors: '+item['authors'],'Version: '+item['version'],'License declared in the official JAR: '+str(item.get('license')),'Official file: '+item['source'],'']
 credits+=['## All included mods / Todos os mods','']+['- '+name+': '+url for name,url in sorted(links)]
 readme='''ATLAS COBBLEMON — 1.0.1
Minecraft Java 1.21.1 | Fabric Loader 0.18.0 | Java 21

INSTALL / INSTALAÇÃO
Import this original ZIP in CurseForge > Minecraft > Import. Do not extract it into mods.
Importe este ZIP original no CurseForge > Minecraft > Importar. Não extraia na pasta mods.
The app downloads official files from manifest.json; approved external mods are in overrides/mods.
O aplicativo baixa os arquivos oficiais do manifest; os externos aprovados estão em overrides/mods.

START / INICIAR
Use Java 21. Start with 6 GB allocated RAM on a computer with enough free memory;
adjust for your hardware and avoid allocating all system RAM. Log in with your own Minecraft account.
Use Java 21 e comece com 6 GB de RAM se seu computador tiver memória livre suficiente.
Abra o perfil usando sua própria conta Minecraft. O idioma inicial é Português (Brasil).

SERVER / SERVIDOR
Atlas Cobblemon is already listed in Multiplayer: jogar.atlascobblemon.com.br
O Atlas já aparece na lista Multiplayer. The server resource pack is offered on connection.
O pacote de texturas é oferecido ao conectar; não está embutido neste arquivo.
Website / Site: https://www.atlascobblemon.com.br

ACCOUNT / CONTA
Local account registration: /register <password> <confirmation> <recovery-email>
Cadastro local: /register <senha> <confirmacao> <email-de-recuperacao>
Confirm the email using /email confirmar <code>. Never share passwords or codes.
Confirme com /email confirmar <codigo>. Nunca compartilhe senhas ou códigos.

CREDITS / CRÉDITOS
See atlas-info/CREDITS.md and atlas-info/licenses. This profile contains no player saves,
credentials, private configs or Atlas server administration code.
Veja os créditos e licenças. O perfil não contém mundos, contas, senhas ou configurações privadas.

VALIDATION / VALIDAÇÃO
Manifest, exact file hashes, archive structure and declared dependency presence were checked.
A graphical Minecraft client launch and live server connection must still be tested after import.
Manifesto, hashes, estrutura e presença das dependências conferidos. Teste de abertura do cliente
Minecraft e conexão em jogo ainda necessário após importar.
'''
 changelog='''Atlas Cobblemon 1.0.1 — CurseForge packaging fix

- Adds manifest.json at ZIP root, Minecraft 1.21.1 and Fabric Loader 0.18.0.
- References 53 official CurseForge files rather than redistributing their JARs.
- Includes 3 approved external mods as unchanged official binaries with credits/licenses.
- Adds server-list entry, Brazilian Portuguese language default, installation notes and complete mod list.
- Preserves the versions from the source archive; excludes Cobblemon Battle Positions from the public profile because its supplied file could not be resolved to an approved distribution entry.
- Does not contain server worlds, private configuration, accounts or credentials.
- Corrects the previous "Missing manifest.json file" rejection. Final approval remains with CurseForge moderation.
'''
 entries['manifest.json']=json.dumps(manifest,indent=2,ensure_ascii=False).encode();entries['modlist.html']=('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Atlas Cobblemon — Mod List</title></head><body><h1>Atlas Cobblemon 1.0.1</h1><p>Minecraft 1.21.1 / Fabric 0.18.0 / Java 21</p><ul>'+''.join('<li><a href="'+html.escape(url,quote=True)+'">'+html.escape(name)+'</a></li>' for name,url in sorted(links))+'</ul></body></html>').encode()
 entries['overrides/']=b'';entries['overrides/servers.dat']=server_list();entries['overrides/options.txt']=b'lang:pt_br\n';entries['overrides/atlas-info/README.txt']=readme.encode();entries['overrides/atlas-info/CREDITS.md']='\n'.join(credits).encode();entries['overrides/atlas-info/CHANGELOG.txt']=changelog.encode()
 for name in entries:
  if name.startswith('/') or '..' in pathlib.PurePosixPath(name).parts or '\\' in name:raise ValueError('Unsafe output path')
 output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in sorted(entries.items()):
   info=zipfile.ZipInfo(name,(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None
  assert all(n in {'manifest.json','modlist.html'} or n.startswith('overrides/') for n in z.namelist())
  assert len(json.loads(z.read('manifest.json'))['files'])==53
 report={'source':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'mods':inventory,'excluded':excluded_files,'checks':{'crc':True,'exactOfficialHashes':True,'dependencyIdsPresent':True,'clientLaunchTested':False,'curseForgeAppExported':False}}
 (work/'build-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));(work/'manifest.json').write_bytes(entries['manifest.json']);output.with_suffix('.sha256').write_text(report['sha256']+'  '+output.name+'\n');(output.parent/'Atlas-Cobblemon-Creditos.md').write_text('\n'.join(credits)+'\n');(output.parent/'Atlas-Cobblemon-Changelog-1.0.1.txt').write_text(changelog)
 print(json.dumps({'output':str(output),'bytes':output.stat().st_size,'curseForgeFiles':len(manifest['files']),'externalMods':len(external),'includedMods':len(inventory),'excluded':excluded_files,'sha256':report['sha256']},indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('source',type=pathlib.Path);parser.add_argument('catalogue',type=pathlib.Path);parser.add_argument('output',type=pathlib.Path);args=parser.parse_args();build(args.source,args.catalogue,args.output)
