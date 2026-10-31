from pathlib import Path
import zipfile,json,collections,argparse
p=argparse.ArgumentParser();p.add_argument("--mods",type=Path,required=True);p.add_argument("--catalogue",type=Path,required=True);a=p.parse_args()
root=a.mods;catalog=json.loads(a.catalogue.read_text());wanted={r['species'] for c in catalog['crates'] for r in c['rewards']};evidence=collections.defaultdict(list);models=set();posers=set();textures=set();resolvers=[]
for jar in root.glob('*.jar'):
 with zipfile.ZipFile(jar) as z:
  for n in z.namelist():
   if n.endswith('.json') and '/species_additions/' in n:
    try:d=json.loads(z.read(n))
    except Exception:continue
    target=d.get('target','').split(':')[-1]
    if target in wanted and 'implemented' in d:evidence[target].append({'file':jar.name,'path':n,'implemented':d['implemented']})
   if '/client/render/models/blockbench/pokemon/' in n and n.endswith('Model.class') and '$' not in n:
    posers.add('cobblemon:'+Path(n).stem.removesuffix('Model').lower())
   if not n.startswith('assets/'):continue
   parts=n.split('/');ns=parts[1];f=parts[-1]
   if '/bedrock/pokemon/models/' in n and f.endswith('.json'):models.add(ns+':'+f[:-5])
   if '/bedrock/pokemon/posers/' in n and f.endswith('.json'):posers.add(ns+':'+f[:-5])
   if '/textures/pokemon/' in n and f.endswith('.png'):textures.add(ns+':'+ '/'.join(parts[2:]))
   if '/bedrock/pokemon/resolvers/' in n and f.endswith('.json'):
    try:d=json.loads(z.read(n))
    except Exception:continue
    if d.get('species','').split(':')[-1] in wanted:resolvers.append((jar.name,n,d))
visual=collections.defaultdict(lambda: {'normal':[],'shiny':[]})
for jar,path,d in resolvers:
 species=d['species'].split(':')[-1];inherited={}
 # Resolver variations inherit properties from prior matching entries. Restrict to base/no extra aspects.
 for v in d.get('variations',[]):
  aspects=v.get('aspects',[])
  if any(x!='shiny' for x in aspects):continue
  merged={**inherited,**v}
  if not aspects:inherited=merged
  if merged.get('model') in models and merged.get('poser') in posers and merged.get('texture') in textures:
   visual[species]['shiny' if 'shiny' in aspects else 'normal'].append({'file':jar,'path':path,'model':merged['model'],'poser':merged['poser'],'texture':merged['texture']})
for c in catalog['crates']:
 for r in c['rewards']:
  r['speciesAdditionEvidence']=evidence[r['species']]
  r['dataImplementationConfirmed']=r['baseImplemented'] or r.get('addonImplemented') is True or any(x['implemented'] for x in evidence[r['species']])
  r['visualEvidence']=visual[r['species']]['shiny' if r['shiny'] else 'normal']
  r['installedAssetsConfirmed']=bool(r['visualEvidence'])
  r['validation']='data_and_assets_confirmed_runtime_pending' if r['dataImplementationConfirmed'] and r['installedAssetsConfirmed'] else 'requires_review'
a.catalogue.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
for c in catalog['crates']:
 ls=[r for r in c['rewards'] if not r['shiny']];print(c['generation'],len(ls),'data',sum(r['dataImplementationConfirmed'] for r in ls),'normal',sum(r['installedAssetsConfirmed'] for r in ls),'shiny',sum(r['installedAssetsConfirmed'] for r in c['rewards'] if r['shiny']))
print('PENDING',[(r['species'],r['shiny'],r['dataImplementationConfirmed'],r['installedAssetsConfirmed']) for c in catalog['crates'] for r in c['rewards'] if r['validation']=='requires_review'])
