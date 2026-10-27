#!/usr/bin/env python3
"""Export only public crate contents and original display assets for a LOCAL preview.

Snapshot input contains no accounts, credentials, delivery history or world data.
Assets are not copied into atlas-web/public: publication requires the authors' grant.
"""
import argparse, collections, hashlib, json, pathlib, re, shutil, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
REGIONS = ['Kanto','Johto','Hoenn','Sinnoh','Unova','Kalos','Alola','Galar','Paldea']
DISPLAY_POSES = {'articuno':'fly','zapdos':'fly','moltres':'fly','yveltal':'fly',
                 'mew':'standing','mewtwo':'standing','regirock':'standing','regice':'standing','registeel':'standing','zarude':'standing','eternatus':'fly'}
HIDDEN_PREVIEWS = {'cosmoem'}
BEDROCK = re.compile(r'(?:q\.)?bedrock\(\s*[\'\"]?([\w-]+)[\'\"]?\s*,\s*[\'\"]?([\w-]+)[\'\"]?\s*\)')
PROCEDURAL = re.compile(r'q\.(biped_walk|bimanual_swing)\(([^)]+)\)')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mods', required=True, type=pathlib.Path)
    p.add_argument('--snapshot', required=True, type=pathlib.Path)
    p.add_argument('--output', required=True, type=pathlib.Path)
    args = p.parse_args()
    output = args.output.resolve()
    if 'atlas-web/public' in str(output):
        p.error('Use a private preview directory; author authorization is required before publication.')
    definitions = json.loads((ROOT/'generations.catalogue.json').read_text())
    snapshot = json.loads(args.snapshot.read_text())
    source = {r['species']:r for c in definitions['crates'] for r in c['rewards'] if not r['shiny']}
    jars = [(f.name,zipfile.ZipFile(f)) for f in args.mods.glob('*.jar')]
    # Installed source references are authoritative; base is loaded before add-on overrides.
    jars.sort(key=lambda x:(0 if x[0].startswith('Cobblemon-fabric-') else 1 if x[0].startswith('mega_showdown-') else 2,x[0]))
    by_jar = dict(jars)
    index = {n:(name,z) for name,z in jars for n in z.namelist() if n.startswith('assets/')}
    models, posers, animations = {}, {}, {}
    for path,(name,z) in index.items():
        if '/bedrock/pokemon/' not in path or not path.endswith('.json'):continue
        kind = path.split('/bedrock/pokemon/')[1].split('/')[0]
        key = path.split('/')[1]+':'+pathlib.Path(path).stem
        if kind=='models':models[key]=path
        elif kind=='posers':posers[key]=path
        elif kind=='animations':
            for key,value in json.loads(z.read(path)).get('animations',{}).items():animations[key]=(value,name,path)
    def read(path):return index[path][1].read(path)
    def animation_name(call):
        match=BEDROCK.search(call)
        return 'animation.'+'.'.join(match.groups()) if match else None
    # Resolve the effective installed resource paths first. A mod may replace a
    # resolver with the same path but point it to a DIFFERENT geometry/poser.
    # The historical evidence list is not a resource-pack precedence list.
    effective_resolvers = collections.defaultdict(list)
    for path,(jar,z) in index.items():
        if '/bedrock/pokemon/resolvers/' not in path or not path.endswith('.json'):continue
        data=json.loads(z.read(path));species=data.get('species','').split(':')[-1]
        normal={};shiny={}
        base_aspects={'neutral-mode'} if species=='xerneas' else set()
        for variation in data.get('variations',[]):
            aspects=set(variation.get('aspects',[]))
            if aspects==base_aspects:normal={**normal,**variation}
            elif aspects==base_aspects|{'shiny'}:shiny={**normal,**variation}
        if all(k in normal and k in shiny for k in ('model','poser','texture')):
            effective_resolvers[species].append((data.get('order',0),path,normal,shiny))
    def export_asset(species):
        entry=source[species]
        if not effective_resolvers[species]:raise ValueError('No normal/shiny resolver: '+species)
        _,resolver_path,normal,shiny=max(effective_resolvers[species],key=lambda x:(x[0],x[1]))
        assert normal['model']==shiny['model'] and normal['poser']==shiny['poser'], species
        directory=output/'pokemon'/'keys'/species;directory.mkdir(parents=True,exist_ok=True)
        geo_path=models[normal['model']];model=json.loads(read(geo_path))
        poser_path=posers.get(normal['poser']);poser=json.loads(read(poser_path)) if poser_path else {}
        poses=poser.get('poses',{})
        eligible=[(key,v) for key,v in poses.items() if not v.get('isBattle') and not key.startswith(('ride','mount'))]
        selected=next(((k,v) for k,v in eligible if k==DISPLAY_POSES.get(species)),None)
        if not selected:selected=next(((k,v) for k,v in eligible if k in ('walking','walk')),None)
        if not selected:selected=next(((k,v) for k,v in eligible if 'WALK' in v.get('poseTypes',[])),None)
        if not selected:selected=next(((k,v) for k,v in eligible if any(t in v.get('poseTypes',[]) for t in ('FLY','SWIM'))),None)
        calls=[s for s in (selected[1].get('animations',[]) if selected else []) if isinstance(s,str)]
        selected_animations=[];procs=[]
        for call in calls:
            name=animation_name(call)
            if name and name in animations and name not in [a['name'] for a in selected_animations]:
                value,jar,path=animations[name];selected_animations.append({'name':name,'data':value,'source':jar,'path':path})
            match=PROCEDURAL.search(call)
            if match:
                values=[v.strip().strip('\'\"') for v in match[2].split(',')]
                assert len(values)==4,(species,call)
                procs.append({'kind':match[1],'speed':float(values[0]),'amplitude':float(values[1]),'left':values[2],'right':values[3]})
        if species in {'articuno','zapdos','moltres'}:
            procs.append({'kind':'wing_flap','speed':1,'amplitude':0.5,'left':'wing_open_left','right':'wing_open_right'})
        if not selected_animations:
            # Compiled Cobblemon posers (e.g. Xerneas) have no JSON pose definition.
            for suffix in ('ground_walk','walk','air_fly','air_walk','swim','ground_idle','air_idle'):
                match=next((name for name in animations if name.startswith('animation.'+species+'.') and name.endswith('.'+suffix)),None)
                if match:
                    value,jar,path=animations[match];selected_animations=[{'name':match,'data':value,'source':jar,'path':path}];break
        if not selected_animations:raise ValueError('No original animation for '+species)
        label='Caminhada'
        anim_names=' '.join(a['name'] for a in selected_animations)
        if not procs and not re.search(r'walk|run',anim_names):label='Flutuação' if 'fly' not in anim_names else 'Voo'
        if selected and any(t in selected[1].get('poseTypes',[]) for t in ('FLY','HOVER')) and 'WALK' not in selected[1].get('poseTypes',[]):label='Voo'
        if DISPLAY_POSES.get(species)=='standing':label='Repouso'
        transforms=selected[1].get('transformedParts',[]) if selected else []
        # Web presentation motion for original poses containing only fixed offsets.
        # This is explicitly separate from original Bedrock animation data.
        motion = {'kind':'float','amplitude':0.015} if species in {'mew','eternatus'} else {'kind':'breathe','amplitude':0.006} if species in {'mewtwo','regirock','regice','registeel','zarude'} else None
        provenance={'resolver':{'source':index[resolver_path][0],'path':resolver_path},'model':{'source':index[geo_path][0],'path':geo_path},'poser':{'source':index[poser_path][0],'path':poser_path} if poser_path else {'compiled':normal['poser']},'textures':{}}
        for variant,e in [('normal',normal),('shiny',shiny)]:
            ns,path=e['texture'].split(':',1);texture_path='assets/'+ns+'/'+path
            (directory/(variant+'.png')).write_bytes(read(texture_path))
            provenance['textures'][variant]={'source':index[texture_path][0],'path':texture_path,'sha256':hashlib.sha256(read(texture_path)).hexdigest()}
        layers={}
        for variant,e in [('normal',normal),('shiny',shiny)]:
            layers[variant]=[]
            for i,layer in enumerate(e.get('layers',[])):
                reference=layer.get('texture')
                if not isinstance(reference,str):raise ValueError('Unsupported texture layer: '+species)
                ns,path=reference.split(':',1);layer_path='assets/'+ns+'/'+path
                name=f'{variant}-layer-{i}.png';(directory/name).write_bytes(read(layer_path))
                layers[variant].append({'texture':name,'emissive':bool(layer.get('emissive')),'translucent':bool(layer.get('translucent'))})
                provenance['textures'][name]={'source':index[layer_path][0],'path':layer_path,'sha256':hashlib.sha256(read(layer_path)).hexdigest()}
        data={'model':model,'animations':[a['data'] for a in selected_animations],'procedural':procs,'transforms':transforms,'normal':'normal.png','shiny':'shiny.png','layers':layers,'presentationMotion':motion}
        raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();version=hashlib.sha256(raw+b''.join(f.read_bytes() for f in sorted(directory.glob('*.png')))).hexdigest()[:12]
        (directory/'model.json').write_bytes(raw)
        (directory/'sources.json').write_text(json.dumps({**provenance,'animations':[{k:v for k,v in a.items() if k!='data'} for a in selected_animations]},indent=2)+'\n')
        license_path=str(pathlib.PurePosixPath(geo_path).parent/'license')
        if license_path in index:(directory/'LICENSE.txt').write_bytes(read(license_path))
        return {'species':species,'name':entry['displayName'],'classification':entry['classification'],'modelUrl':f'/pokemon/keys/{species}/model.json?v={version}','animation':label,'generation':next(c['generation'] for c in definitions['crates'] if any(r['species']==species for r in c['rewards']))}
    wanted=sorted({r['species'] for c in snapshot['crates'] for r in c['rewards']})
    output.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'licenses', output/'licenses', dirs_exist_ok=True)
    entries={s:export_asset(s) for s in wanted}
    crates=[]
    for crate in snapshot['crates']:
        rewards=collections.OrderedDict()
        for r in crate['rewards']:rewards.setdefault(r['species'],{})['shiny' if r['shiny'] else 'normal']=True
        assert all(set(v)=={'normal','shiny'} for v in rewards.values()),crate['identifier']
        generation=int(crate['identifier'].split('_')[1]) if crate['identifier'].startswith('generation_') else None
        crates.append({'identifier':crate['identifier'],'name':f'Chave {generation}ª geração — {REGIONS[generation-1]}' if generation else 'Chave Lendários do mês','generation':generation,'region':REGIONS[generation-1] if generation else None,'period':snapshot['monthlyPeriod'] if not generation else None,'species':[entries[s] for s in rewards if s not in HIDDEN_PREVIEWS], 'hiddenPreviews':[entries[s]['name'] for s in rewards if s in HIDDEN_PREVIEWS]})
    catalogue={'schemaVersion':1,'generatedAt':snapshot['generatedAt'],'crates':crates}
    (output/'catalogue.json').write_text(json.dumps(catalogue,ensure_ascii=False,separators=(',',':'))+'\n')
    (output/'NOTICE.txt').write_text('LOCAL PREVIEW — not cleared for commercial publication.\nOriginal assets: Cobblemon and Mega Showdown, with original authors retaining rights.\nCobblemon: https://gitlab.com/cable-mc/cobblemon-assets\nMega Showdown: https://github.com/yajatkaul/CobblemonMegaShowdown/blob/main/LICENSE.md\nMega Showdown asset license: CC BY-NC-SA 4.0; commercial use requires explicit written authorization.\nAn archived copy of the original Mega Showdown license is in licenses/Mega-Showdown-v2.1.md.\nPer-model source paths and unchanged asset hashes are in sources.json.\nModels and animation data are preserved; the web adapter interprets them at runtime.\nPokémon belongs to its respective rights holders.\n')
    print(json.dumps({'crates':len(crates),'species':len(entries),'variants':len(entries)*2,'animationLabels':dict(collections.Counter(e['animation'] for e in entries.values())),'bytes':sum(f.stat().st_size for f in output.rglob('*') if f.is_file()),'output':str(output)}))

if __name__=='__main__':main()
