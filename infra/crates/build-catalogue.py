#!/usr/bin/env python3
"""Build a disabled, reviewable crate catalogue from installed Cobblemon data."""
import argparse,json,re,zipfile,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mods',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=next(a.mods.glob('Cobblemon-fabric-1.8.2*.jar'))
regions=['Kanto','Johto','Hoenn','Sinnoh','Unova','Kalos','Alola','Galar','Paldea']
positions=[(1240,85,4021),(1246,85,4021),(1243,92,4021),(1243,98,4022),(1243,104,4022),(1243,110,4022),(1243,115,4022),(1242,120,4021),(1244,120,4021)]
crates=[dict(identifier=f'generation_{g}',generation=g,region=regions[g-1],enabled=False,dimension='atlas:emerald',position=dict(zip(('x','y','z'),positions[g-1])),rewards=[]) for g in range(1,10)]
with zipfile.ZipFile(base) as z:
 for name in sorted(z.namelist()):
  m=re.fullmatch(r'data/cobblemon/species/generation(\d+)\w*/([^/]+)\.json',name)
  if not m:continue
  s=json.loads(z.read(name));labels=s.get('labels',[])
  if not {'legendary','mythical'}.intersection(labels):continue
  g=int(m[1]);species=m[2]
  for shiny in (False,True):
   crates[g-1]['rewards'].append(dict(identifier=f'{species}_{"shiny" if shiny else "normal"}',species=species,displayName=s['name'],classification='mythical' if 'mythical' in labels else 'legendary',shiny=shiny,form='base',weight=None,baseImplemented=s.get('implemented',False),validation='pending_runtime_and_client_assets',enabled=False))
# Include installed addon data without treating static declarations as runtime certification.
addon_overrides={}
for addon in sorted(a.mods.glob('mega_showdown-*.jar')):
 with zipfile.ZipFile(addon) as z:
  for name in z.namelist():
   if '/species/' in name and name.endswith('.json'):
    addon_overrides[Path(name).stem]=json.loads(z.read(name))
# species_additions targets the species ID; filenames can describe forms instead.
for addon in sorted(a.mods.glob('*.jar')):
 with zipfile.ZipFile(addon) as z:
  for name in z.namelist():
   if '/species_additions/' in name and name.endswith('.json'):
    try:v=json.loads(z.read(name))
    except (ValueError,UnicodeDecodeError):continue
    if 'implemented' in v:
     target=v.get('target','').split(':')[-1]
     addon_overrides.setdefault(target,{})['implemented']=v['implemented']
for c in crates:
 for r in c['rewards']:
  r['addonImplemented']=addon_overrides.get(r['species'],{}).get('implemented')
  r['dataImplementationConfirmed']=r['baseImplemented'] or r['addonImplemented'] is True
  if r['dataImplementationConfirmed']:r['validation']='data_confirmed_assets_and_runtime_pending'
for c in crates:
 c['rewards'].sort(key=lambda r:(r['displayName'],r['shiny']))
result=dict(schemaVersion=1,status='draft_not_active',source=dict(file=base.name,sha256=hashlib.sha256(base.read_bytes()).hexdigest()),policy=dict(categories=['legendary','mythical'],variants=['normal','shiny'],generation='species_debut',forms='base_only_pending_review',probabilities='not_defined',keys='not_defined',level='not_defined',monthlyRotation='separate_not_configured'),crates=crates)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
report=['# Atlas — catálogo das caixas por geração','', 'Rascunho: sorteios desativados. Normal e shiny são prêmios distintos. Chances, nível e obtenção de chaves ainda não definidos. Formas alternativas aguardam revisão.','', '| Geração | Região | Espécies | Prêmios | Marcadas implementadas no mod base |','|---|---|---:|---:|---:|']
for c in crates:
 report.append(f'| {c["generation"]} | {c["region"]} | {len(c["rewards"])//2} | {len(c["rewards"])} | {sum(r["baseImplemented"] for r in c["rewards"])//2} |')
for c in crates:
 report+=['',f'## {c["generation"]}ª geração — {c["region"]}','',*['- '+r['displayName']+' — '+r['classification']+('' if r['baseImplemented'] else ' (pendente no mod base)') for r in c['rewards'] if not r['shiny']]]
report+=['','A marca implemented do mod base não certifica modelos/texturas nem suporte em addons e datapacks. Todos os prêmios exigem validação no registro ativo e cliente antes de habilitar. Ultra Beasts e Paradoxos sem classificação lendária/mítica não entram. A caixa mensal fica separada.']
a.output.with_suffix('.md').write_text('\n'.join(report)+'\n')
assert len(crates)==9
for c in crates:
 assert len({r['identifier'] for r in c['rewards']})==len(c['rewards'])
 assert len(c['rewards'])%2==0
 assert all(not r['enabled'] and r['weight'] is None for r in c['rewards'])
print(json.dumps({'species':sum(len(c['rewards'])//2 for c in crates),'rewards':sum(len(c['rewards']) for c in crates),'crates':len(crates),'enabled':False}))
