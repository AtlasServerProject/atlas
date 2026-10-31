#!/usr/bin/env python3
"""Read-only analysis of which implemented Cobblemon species can spawn in a built area.

Reads spawn pools, presets, species and biome tags straight from the installed server jars, merges preset
conditions, resolves biome tags and decides per spawn entry whether a constructed area could satisfy it:
biomes come from /fillbiome, blocks/fluids/sky/light are buildable, time/weather/moon/lures happen over time.
World-generated structures cannot be built. Height is the scenario parameter (list of available Y ranges).
"""
import argparse, collections, io, json, pathlib, re, zipfile

SERVER = pathlib.Path('/opt/atlas/server/fabric')

def sources():
    jars = [SERVER / 'versions/1.21.1/server-1.21.1.jar'] + sorted((SERVER / 'mods').glob('*.jar'))
    for jar in jars:
        z = zipfile.ZipFile(jar)
        yield jar.name, z
        for n in z.namelist():
            if n.startswith('META-INF/jars/') and n.endswith('.jar') and 'convention-tags-v2' in n:
                yield n, zipfile.ZipFile(io.BytesIO(z.read(n)))

def load():
    tags, biomes, pools, presets, species = collections.defaultdict(set), set(), [], {}, {}
    global BLOCK_TAGS; BLOCK_TAGS = collections.defaultdict(set)
    for name, z in sources():
        for n in z.namelist():
            if not n.endswith('.json'): continue
            m = re.match(r'data/([^/]+)/tags/worldgen/biome/(.+)\.json$', n)
            if m:
                d = json.loads(z.read(n)); key = f'{m[1]}:{m[2]}'
                if d.get('replace'): tags[key] = set()
                for v in d.get('values', []):
                    tags[key].add(v['id'] if isinstance(v, dict) else v)
                continue
            m = re.match(r'data/([^/]+)/tags/block/(.+)\.json$', n)
            if m:
                d = json.loads(z.read(n)); key = f'{m[1]}:{m[2]}'
                if d.get('replace'): BLOCK_TAGS[key] = set()
                for v in d.get('values', []): BLOCK_TAGS[key].add(v['id'] if isinstance(v, dict) else v)
                continue
            m = re.match(r'data/minecraft/worldgen/biome/(.+)\.json$', n)
            if m: biomes.add('minecraft:' + m[1]); continue
            if re.match(r'data/[^/]+/spawn_pool_world/', n):
                d = json.loads(z.read(n))
                if d.get('enabled', True): pools.extend(d.get('spawns', []))
                continue
            m = re.match(r'data/cobblemon/spawn_detail_presets/(.+)\.json$', n)
            if m: presets[m[1]] = json.loads(z.read(n)); continue
            m = re.match(r'data/cobblemon/species/[^/]+/(.+)\.json$', n)
            if m:
                d = json.loads(z.read(n))
                if d.get('implemented'): species[m[1]] = d.get('labels', [])
    return tags, biomes, pools, presets, species

def resolve(entries, tags, seen=None):
    out, seen = set(), seen or set()
    for e in entries or []:
        if e.startswith('#'):
            if e in seen: continue
            seen.add(e); out |= resolve(tags.get(e[1:], ()), tags, seen)
        else: out.add(e)
    return out

def merge(spawn, presets):
    cond, anti = dict(spawn.get('condition') or {}), dict(spawn.get('anticondition') or {})
    for p in spawn.get('presets', []):
        pre = presets.get(p, {})
        for k, v in (pre.get('condition') or {}).items(): cond.setdefault(k, v)
        for k, v in (pre.get('anticondition') or {}).items(): anti.setdefault(k, v)
    return cond, anti

def satisfiable(cond, anti, all_biomes, tags, y_ranges):
    """Return the set of biomes where the entry can spawn in a built area (empty = impossible)."""
    if cond.get('structures'): return set()
    if 'minX' in cond or 'maxX' in cond: return set()
    lo, hi = cond.get('minY', -64), cond.get('maxY', 320)
    if not any(a <= hi and lo <= b for a, b in y_ranges): return set()
    ok = resolve(cond['biomes'], tags) & all_biomes if cond.get('biomes') else set(all_biomes)
    ok -= resolve(anti.get('biomes'), tags)
    return ok

def species_of(spawn):
    names = []
    if spawn.get('pokemon'): names.append(spawn['pokemon'])
    for h in spawn.get('herdablePokemon', []) or []:
        names.append(h['pokemon'] if isinstance(h, dict) else h)
    return {n.split()[0].split('[')[0].lower() for n in names}

WATER_TYPES = {'submerged', 'seafloor', 'surface', 'fishing'}

def zone_ok(spawn, cond, anti, zone, tags, spawn_y=62):
    """Can this spawn entry happen in this built zone? Mirrors the checks Cobblemon performs."""
    if cond.get('structures') or cond.get('isSlimeChunk') or 'minX' in cond or 'maxX' in cond: return False
    if not cond.get('minY', -64) <= spawn_y <= cond.get('maxY', 320): return False
    biome = zone['biome']
    if cond.get('biomes') and biome not in resolve(cond['biomes'], tags): return False
    if biome in resolve(anti.get('biomes'), tags): return False
    blocks = set(zone['blocks'])
    for key in ('neededNearbyBlocks', 'neededBaseBlocks'):
        if cond.get(key) and not resolve(cond[key], BLOCK_TAGS) & blocks: return False
    fluid = cond.get('fluid', '')
    if 'lava' in fluid and not zone['lava']: return False
    if ('water' in fluid or spawn.get('spawnablePositionType') in WATER_TYPES) and not zone['water']: return False
    if cond.get('canSeeSky') is False or cond.get('maxSkyLight', 15) < 8:
        if not zone['covered']: return False
    if (cond.get('canSeeSky') is True or cond.get('minSkyLight', 0) >= 8) and not (zone['open_sky'] or zone['covered']): return False
    return True

def evaluate_zones(path):
    tags, biomes, pools, presets, species = load()
    implemented, zones = set(species), json.loads(pathlib.Path(path).read_text())
    reach, per_zone = set(), collections.Counter()
    for s in pools:
        cond, anti = merge(s, presets); names = species_of(s) & implemented
        if not names: continue
        ok = [z['biome'] for z in zones if zone_ok(s, cond, anti, z, tags)]
        if ok:
            reach |= names
            for b in set(ok): per_zone[b] += len(names)
    print(f'SafariVip construida: {len(reach)}/{len(implemented)} especies = {100 * len(reach) / len(implemented):.1f}%')
    return reach, per_zone, implemented

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--json'); ap.add_argument('--zones'); a = ap.parse_args()
    if a.zones:
        evaluate_zones(a.zones); return
    tags, biomes, pools, presets, species = load()
    implemented = set(species)
    scenarios = {'superficie (Y 62 a 120)': [(62, 120)], 'superficie + cavernas (Y -60 a 13 e 62 a 120)': [(-60, 13), (62, 120)],
                 'todas as alturas': [(-64, 320)]}
    print(f'biomas vanilla: {len(biomes)} | especies implementadas: {len(implemented)} | regras: {len(pools)}')
    report = {}
    for label, yr in scenarios.items():
        per_species = collections.defaultdict(set); structure_only = set()
        for s in pools:
            cond, anti = merge(s, presets)
            names = species_of(s) & implemented
            ok = satisfiable(cond, anti, biomes, tags, yr)
            for n in names: per_species[n] |= ok
            if cond.get('structures'): structure_only |= names
        reach = {n for n, b in per_species.items() if b}
        print(f'\n[{label}] alcançáveis: {len(reach)}/{len(implemented)} = {100 * len(reach) / len(implemented):.1f}%')
        report[label] = {n: sorted(b) for n, b in per_species.items() if b}
        if label.startswith('superficie + cavernas'):
            without = implemented - set(per_species)
            only_struct = {n for n in implemented - reach if n in per_species or n in structure_only}
            print('  sem nenhuma regra de spawn natural:', len(without))
            print('  com regra, mas só em estrutura/altura impossível:', len(implemented - reach - without))
            # Greedy minimal biome set reaching the same coverage.
            remaining, chosen = set(reach), []
            while remaining:
                best = max(biomes, key=lambda b: sum(1 for n in remaining if b in per_species[n]))
                gain = {n for n in remaining if best in per_species[n]}
                if not gain: break
                chosen.append((best, len(gain))); remaining -= gain
            acc = 0
            print('  biomas em ordem de ganho (guloso):')
            for i, (b, g) in enumerate(chosen, 1):
                acc += g; print(f'   {i:2}. {b:40} +{g:3}  acumulado {acc} ({100 * acc / len(implemented):.1f}%)')
    if a.json: pathlib.Path(a.json).write_text(json.dumps(report, indent=1))

if __name__ == '__main__':
    main()
