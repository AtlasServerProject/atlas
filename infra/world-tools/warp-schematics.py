#!/usr/bin/env python3
"""Generate the VIP, Raid, Safari and SafariVip warp builds as Litematica schematics (+ top-down previews).

Pure Python, deterministic (fixed seeds). Each build is a 128x128 floating island in the Atlas palette:
quartz, white/cyan concrete, dark oak, polished blackstone and sea lanterns. Output: <out>/<name>.litematic,
<name>-preview.png and warps.json with the arrival point of each build (relative to the schematic origin).
"""
import argparse, array, gzip, json, math, pathlib, random, struct, time, zlib

SIZE, HEIGHT, SURFACE = 128, 56, 16      # x/z size, y size, y of the walkable surface
DATA_VERSION = 3955                      # Minecraft 1.21.1

# ---------------------------------------------------------------- NBT / Litematica
class Int(int): pass
class Long(int): pass
class LongArray(list): pass

def _payload(value):
    if isinstance(value, bool): raise TypeError('use Int for booleans')
    if isinstance(value, Long): return 4, struct.pack('>q', value)
    if isinstance(value, Int): return 3, struct.pack('>i', value)
    if isinstance(value, str):
        data = value.encode('utf-8'); return 8, struct.pack('>H', len(data)) + data
    if isinstance(value, LongArray):
        return 12, struct.pack('>i', len(value)) + b''.join(struct.pack('>q', v) for v in value)
    if isinstance(value, list):
        if not value: return 9, b'\x00' + struct.pack('>i', 0)
        items = [_payload(v) for v in value]
        return 9, bytes([items[0][0]]) + struct.pack('>i', len(items)) + b''.join(p for _, p in items)
    if isinstance(value, dict):
        out = b''
        for key, item in value.items():
            tag, payload = _payload(item); name = key.encode('utf-8')
            out += bytes([tag]) + struct.pack('>H', len(name)) + name + payload
        return 10, out + b'\x00'
    raise TypeError(type(value))

def nbt(root):
    tag, payload = _payload(root)
    return bytes([tag]) + struct.pack('>H', 0) + payload

# ---------------------------------------------------------------- build volume
class Build:
    def __init__(self, name, seed):
        self.name, self.rng = name, random.Random(seed)
        self.palette, self.index = ['minecraft:air'], {'minecraft:air': 0}
        self.cells = array.array('H', bytes(2 * SIZE * HEIGHT * SIZE))
        self.arrival = None
        self.notes = {}

    def id(self, block):
        if block not in self.index:
            self.index[block] = len(self.palette); self.palette.append(block)
        return self.index[block]

    def set(self, x, y, z, block):
        if 0 <= x < SIZE and 0 <= y < HEIGHT and 0 <= z < SIZE:
            self.cells[(y * SIZE + z) * SIZE + x] = self.id(block)

    def get(self, x, y, z):
        if 0 <= x < SIZE and 0 <= y < HEIGHT and 0 <= z < SIZE:
            return self.palette[self.cells[(y * SIZE + z) * SIZE + x]]
        return 'minecraft:air'

    def box(self, x0, y0, z0, x1, y1, z1, block):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    self.set(x, y, z, block)

    def disc(self, cx, y, cz, r, block, inner=-1.0):
        for z in range(int(cz - r) - 1, int(cz + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                d = math.hypot(x - cx, z - cz)
                if inner < d <= r: self.set(x, y, z, block)

    def litematic(self, author='Atlas Cobblemon'):
        bits = max(2, (len(self.palette) - 1).bit_length())
        volume = SIZE * HEIGHT * SIZE
        longs = [0] * ((volume * bits + 63) // 64)
        for i, v in enumerate(self.cells):
            if not v: continue
            pos = i * bits; li, off = pos >> 6, pos & 63
            longs[li] |= (v << off) & 0xFFFFFFFFFFFFFFFF
            if off + bits > 64: longs[li + 1] |= v >> (64 - off)
        signed = LongArray(l - (1 << 64) if l >= 1 << 63 else l for l in longs)
        palette = []
        for block in self.palette:
            name, _, props = block.partition('[')
            entry = {'Name': name}
            if props:
                entry['Properties'] = dict(p.split('=') for p in props.rstrip(']').split(','))
            palette.append(entry)
        now = Long(int(time.time() * 1000))
        size = {'x': Int(SIZE), 'y': Int(HEIGHT), 'z': Int(SIZE)}
        total = sum(1 for v in self.cells if v)
        root = {
            'MinecraftDataVersion': Int(DATA_VERSION), 'Version': Int(7), 'SubVersion': Int(1),
            'Metadata': {'Name': f'Atlas Warp {self.name}', 'Author': author,
                         'Description': f'Warp {self.name} do Atlas Cobblemon. Chegada: {self.arrival}',
                         'RegionCount': Int(1), 'TotalBlocks': Int(total), 'TotalVolume': Int(volume),
                         'TimeCreated': now, 'TimeModified': now, 'EnclosingSize': size},
            'Regions': {self.name: {'Position': {'x': Int(0), 'y': Int(0), 'z': Int(0)}, 'Size': size,
                                    'BlockStatePalette': palette, 'BlockStates': signed,
                                    'TileEntities': [], 'Entities': [], 'PendingBlockTicks': [], 'PendingFluidTicks': []}},
        }
        return gzip.compress(nbt(root), mtime=0)

# ---------------------------------------------------------------- shared pieces
def noise2(seed, scale):
    """Smooth value noise in [0,1]."""
    rng = random.Random(seed); grid = {}
    def val(ix, iz):
        if (ix, iz) not in grid: grid[(ix, iz)] = rng.random()
        return grid[(ix, iz)]
    def at(x, z):
        fx, fz = x / scale, z / scale; ix, iz = math.floor(fx), math.floor(fz); tx, tz = fx - ix, fz - iz
        sx, sz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
        a = val(ix, iz) + (val(ix + 1, iz) - val(ix, iz)) * sx
        b = val(ix, iz + 1) + (val(ix + 1, iz + 1) - val(ix, iz + 1)) * sx
        return a + (b - a) * sz
    return at

def island(b, radius, top='minecraft:grass_block', heights=None):
    """Floating island: rugged rock underside, dirt layers, chosen top. Returns {(x,z): surface_y}."""
    edge = noise2(b.rng.random(), 9); depth = noise2(b.rng.random(), 7); surface = {}
    for z in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - 63.5, z - 63.5) / (radius * (0.9 + 0.12 * edge(x, z)))
            if d > 1: continue
            sy = SURFACE if heights is None else heights(x, z)
            bottom = SURFACE - 2 - int((1 - d * d) * (SURFACE - 3) * (0.7 + 0.3 * depth(x, z)))
            for y in range(max(0, bottom), sy + 1):
                if y == sy: block = top
                elif y >= sy - 3: block = 'minecraft:dirt'
                else: block = b.rng.choice(['minecraft:stone'] * 6 + ['minecraft:andesite', 'minecraft:tuff', 'minecraft:deepslate'])
                b.set(x, y, z, block)
            surface[(x, z)] = sy
    return surface

def pokeball(b, cx, y, cz, r, colours=('minecraft:cyan_concrete', 'minecraft:white_concrete')):
    """Floor emblem in Atlas colours: cyan top, white bottom, dark band and button."""
    for z in range(cz - r, cz + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x - cx, z - cz)
            if d > r + 0.3: continue
            if d > r - 0.9: block = 'minecraft:polished_blackstone'
            elif d <= r * 0.22: block = colours[1] if d <= r * 0.12 else 'minecraft:polished_blackstone'
            elif abs(z - cz) <= max(1, r // 6): block = 'minecraft:polished_blackstone'
            else: block = colours[0] if z < cz else colours[1]
            b.set(x, y, z, block)

def lamp_post(b, x, y, z, height=3):
    for dy in range(height): b.set(x, y + dy, z, 'minecraft:polished_blackstone_wall')
    b.set(x, y + height, z, 'minecraft:lantern[hanging=false]')

def arrival(b, y=SURFACE, z=114):
    """Southern arrival platform; the warp point stands on the emblem facing north."""
    b.box(56, y, z - 8, 71, y, z + 6, 'minecraft:smooth_quartz')
    b.box(55, y, z - 8, 55, y, z + 6, 'minecraft:cyan_concrete'); b.box(72, y, z - 8, 72, y, z + 6, 'minecraft:cyan_concrete')
    pokeball(b, 63, y, z - 1, 5)
    for x in (56, 71):
        for zz in (z - 8, z + 6): lamp_post(b, x, y + 1, zz, 3)
    b.arrival = {'x': 63, 'y': y + 1, 'z': z - 1, 'yaw': 180}

def flatten(b, surf, x0, z0, x1, z1):
    """Level a rectangle to SURFACE (grass) so buildings are not buried in hills."""
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            if surf.get((x, z)) is None: continue
            for y in range(SURFACE + 1, HEIGHT): b.set(x, y, z, 'minecraft:air')
            b.set(x, SURFACE, z, 'minecraft:grass_block'); surf[(x, z)] = SURFACE

def water_leaks(b):
    leaks = 0
    for y in range(HEIGHT):
        for z in range(SIZE):
            for x in range(SIZE):
                if b.get(x, y, z).startswith('minecraft:water'):
                    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                        if b.get(x + dx, y + dy, z + dz) == 'minecraft:air' or not (0 <= x + dx < SIZE and 0 <= z + dz < SIZE and y + dy >= 0):
                            leaks += 1; break
    return leaks

def tree(b, x, y, z, kind='oak', height=None):
    if not on_ground(b, x, y, z) and b.get(x, y - 1, z) != 'minecraft:dirt': return
    h = height or b.rng.randint(5, 7)
    log, leaves = f'minecraft:{kind}_log[axis=y]', f'minecraft:{kind}_leaves[distance=1,persistent=true,waterlogged=false]'
    if kind == 'spruce':
        for dy in range(h): b.set(x, y + dy, z, log)
        for dy in range(2, h + 2):
            r = max(0, (h + 1 - dy) // 2)
            for dz in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) + abs(dz) <= r + 1 and (dx or dz or dy >= h) and b.get(x + dx, y + dy, z + dz) == 'minecraft:air':
                        b.set(x + dx, y + dy, z + dz, leaves)
        b.set(x, y + h + 1, z, leaves); return
    for dy in range(h): b.set(x, y + dy, z, log)
    r = 3 if kind == 'cherry' else 2
    for dy in range(h - 3, h + 2):
        rr = r if dy < h else r - 1
        for dz in range(-rr, rr + 1):
            for dx in range(-rr, rr + 1):
                if dx * dx + dz * dz + (dy - h) ** 2 * 0.6 <= rr * rr + 1 and b.rng.random() > 0.08 \
                        and b.get(x + dx, y + dy, z + dz) == 'minecraft:air':
                    b.set(x + dx, y + dy, z + dz, leaves)

GROUND = ('minecraft:grass_block', 'minecraft:moss_block', 'minecraft:podzol', 'minecraft:coarse_dirt', 'minecraft:mud', 'minecraft:mycelium')

def on_ground(b, x, y, z):
    return b.get(x, y - 1, z).startswith(GROUND)

def plants(b, x, y, z, flowers):
    if not on_ground(b, x, y, z): return
    roll = b.rng.random()
    if roll < 0.12 and b.get(x, y + 1, z) == 'minecraft:air':
        b.set(x, y, z, 'minecraft:tall_grass[half=lower]'); b.set(x, y + 1, z, 'minecraft:tall_grass[half=upper]')
    elif roll < 0.42: b.set(x, y, z, 'minecraft:short_grass')
    elif roll < 0.52: b.set(x, y, z, 'minecraft:' + b.rng.choice(flowers))

def path_line(b, x0, z0, x1, z1, width, surface, block='minecraft:dirt_path'):
    steps = int(max(abs(x1 - x0), abs(z1 - z0))) + 1
    for i in range(steps):
        t = i / max(1, steps - 1); px, pz = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
        for dz in range(-width, width + 1):
            for dx in range(-width, width + 1):
                x, z = int(round(px + dx)), int(round(pz + dz))
                if (x, z) in surface and dx * dx + dz * dz <= width * width + 1:
                    y = surface[(x, z)]; b.set(x, y, z, block)
                    for dy in (1, 2): b.set(x, y + dy, z, 'minecraft:air')

def hedge(b, surface, radius, kind='azalea'):
    """Walkable-edge hedge two blocks high, with a gap at the southern arrival."""
    leaves = f'minecraft:{kind}_leaves[distance=1,persistent=true,waterlogged=false]'
    for (x, z), y in surface.items():
        d = math.hypot(x - 63.5, z - 63.5)
        if radius - 1.6 < d <= radius and not (z > 100 and 54 <= x <= 73):
            for dy in (1, 2): b.set(x, y + dy, z, leaves)

# ---------------------------------------------------------------- the four builds
def build_vip():
    b = Build('VIP', 1001); surf = island(b, 61)
    arrival(b)
    # Avenue: quartz with cyan borders, embedded sea lanterns and lamp posts.
    for z in range(36, 106):
        for x in range(60, 68): b.set(x, SURFACE, z, 'minecraft:smooth_quartz')
        b.set(59, SURFACE, z, 'minecraft:cyan_concrete'); b.set(68, SURFACE, z, 'minecraft:cyan_concrete')
        if z % 6 == 0: b.set(63, SURFACE, z, 'minecraft:sea_lantern'); b.set(64, SURFACE, z, 'minecraft:sea_lantern')
        if z % 8 == 0: lamp_post(b, 57, SURFACE + 1, z, 4); lamp_post(b, 70, SURFACE + 1, z, 4)
    # Central plaza with fountain.
    b.disc(63.5, SURFACE, 63.5, 20, 'minecraft:smooth_quartz'); b.disc(63.5, SURFACE, 63.5, 20, 'minecraft:cyan_concrete', inner=19)
    b.disc(63.5, SURFACE, 63.5, 13, 'minecraft:chiseled_quartz_block', inner=12)
    b.disc(63.5, SURFACE + 1, 63.5, 7, 'minecraft:quartz_bricks', inner=6)
    b.disc(63.5, SURFACE + 1, 63.5, 6, 'minecraft:water[level=0]'); b.disc(63.5, SURFACE, 63.5, 6, 'minecraft:prismarine_bricks')
    for dy in range(1, 6): b.box(63, SURFACE + dy, 63, 64, SURFACE + dy, 64, 'minecraft:quartz_pillar[axis=y]')
    b.box(63, SURFACE + 6, 63, 64, SURFACE + 6, 64, 'minecraft:sea_lantern'); b.box(63, SURFACE + 7, 63, 64, SURFACE + 7, 64, 'minecraft:gold_block')
    for a in range(0, 360, 45):
        x, z = 63.5 + 17 * math.cos(math.radians(a)), 63.5 + 17 * math.sin(math.radians(a))
        if not (55 < x < 72 and z > 70): lamp_post(b, int(x), SURFACE + 1, int(z), 4)
    # Domed pavilion to the north.
    cx, cz, r = 63.5, 22.5, 13
    b.disc(cx, SURFACE, cz, r + 1, 'minecraft:smooth_quartz'); b.disc(cx, SURFACE, cz, r + 1, 'minecraft:gold_block', inner=r)
    pokeball(b, 63, SURFACE, 22, 6)
    for a in range(0, 360, 30):
        x, z = int(round(cx + r * math.cos(math.radians(a)))), int(round(cz + r * math.sin(math.radians(a))))
        if a == 90: continue  # south opening towards the plaza
        for dy in range(1, 9): b.set(x, SURFACE + dy, z, 'minecraft:quartz_pillar[axis=y]')
    b.disc(cx, SURFACE + 9, cz, r + 1, 'minecraft:chiseled_quartz_block', inner=r - 1)
    b.disc(cx, SURFACE + 9, cz, r + 1.4, 'minecraft:gold_block', inner=r + 0.6)
    for dy in range(1, r + 1):
        rr = math.sqrt(max(0, r * r - dy * dy))
        b.disc(cx, SURFACE + 9 + dy, cz, rr, 'minecraft:cyan_stained_glass', inner=rr - 1.2)
    b.set(63, SURFACE + 9 + r, 22, 'minecraft:sea_lantern'); b.set(63, SURFACE + 10 + r, 22, 'minecraft:end_rod[facing=up]')
    for x in (55, 72):
        for z in (16, 29): b.set(x, SURFACE + 1, z, 'minecraft:dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]' if x == 55 else 'minecraft:dark_oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]')
    # Four gardens: hedged beds, birch trees and benches along the avenue.
    for gx, gz in ((32, 42), (95, 42), (32, 86), (95, 86)):
        for z in range(gz - 9, gz + 10):
            for x in range(gx - 11, gx + 12):
                if (x, z) not in surf: continue
                edge = abs(x - gx) == 11 or abs(z - gz) == 9
                if edge and not (abs(x - gx) <= 1 or abs(z - gz) <= 1):
                    b.set(x, SURFACE + 1, z, 'minecraft:azalea_leaves[distance=1,persistent=true,waterlogged=false]')
                elif not edge: plants(b, x, SURFACE + 1, z, ['allium', 'azure_bluet', 'cornflower', 'oxeye_daisy', 'lily_of_the_valley'])
        tree(b, gx, SURFACE + 1, gz, 'birch', 6)
    for z in range(42, 104, 12):
        b.set(58, SURFACE + 1, z, 'minecraft:dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]')
        b.set(69, SURFACE + 1, z, 'minecraft:dark_oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]')
    for (x, z), y in surf.items():
        if b.get(x, y + 1, z) == 'minecraft:air' and b.get(x, y, z) == 'minecraft:grass_block' and b.rng.random() < 0.18:
            plants(b, x, y + 1, z, ['dandelion', 'poppy'])
    b.notes = {'pavilion': {'x': 63, 'y': SURFACE + 1, 'z': 22}, 'fountain': {'x': 63, 'y': SURFACE + 1, 'z': 63}}
    return b

def build_raid():
    b = Build('Raid', 2002); surf = island(b, 61, top='minecraft:stone')
    rough = noise2(7, 6)
    for (x, z), y in surf.items():
        n = rough(x, z)
        b.set(x, y, z, 'minecraft:moss_block' if n > 0.72 else 'minecraft:andesite' if n > 0.55 else 'minecraft:tuff' if n < 0.25 else 'minecraft:stone')
    arrival(b)
    for z in range(100, 108):
        for x in range(60, 68): b.set(x, SURFACE, z, 'minecraft:polished_blackstone_bricks')
    cx = cz = 63.5
    # Arena floor with cyan rings.
    b.disc(cx, SURFACE, cz, 27, 'minecraft:polished_blackstone_bricks')
    for ring in (10.5, 18.5, 26.5): b.disc(cx, SURFACE, cz, ring, 'minecraft:cyan_concrete', inner=ring - 1)
    # Stepped pedestal; the raid den goes on the chiseled quartz at the top centre.
    for tier, rr in enumerate((7, 5, 3)):
        b.disc(cx, SURFACE + 1 + tier, cz, rr, 'minecraft:polished_deepslate')
        b.disc(cx, SURFACE + 1 + tier, cz, rr, 'minecraft:deepslate_tiles', inner=rr - 1)
    b.box(63, SURFACE + 3, 63, 64, SURFACE + 3, 64, 'minecraft:chiseled_quartz_block')
    for a in range(0, 360, 30):
        x, z = int(round(cx + 9 * math.cos(math.radians(a)))), int(round(cz + 9 * math.sin(math.radians(a))))
        h = 2 + (a // 30) % 3
        for dy in range(1, h + 1): b.set(x, SURFACE + dy, z, 'minecraft:amethyst_block')
        b.set(x, SURFACE + h + 1, z, 'minecraft:amethyst_cluster[facing=up,waterlogged=false]')
    # Stands: rising tiers with cyan seat rows, open at the four cardinal entrances.
    for tier in range(6):
        inner, outer = 29 + tier * 2, 31 + tier * 2
        for z in range(SIZE):
            for x in range(SIZE):
                d = math.hypot(x - cx, z - cz)
                if not inner < d <= outer: continue
                if min(abs(x - cx), abs(z - cz)) < 4: continue
                for dy in range(1, tier + 2): b.set(x, SURFACE + dy, z, 'minecraft:polished_blackstone_bricks')
                if d > outer - 1: b.set(x, SURFACE + tier + 2, z, 'minecraft:cyan_concrete')
    # Outer wall with arches and lit pillars.
    for z in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - cx, z - cz)
            if 41 < d <= 43:
                gate = min(abs(x - cx), abs(z - cz)) < 4
                for dy in range(1, 14):
                    if gate and dy <= 8: continue
                    b.set(x, SURFACE + dy, z, 'minecraft:deepslate_bricks' if dy % 5 else 'minecraft:cyan_concrete')
    for a in range(0, 360, 15):
        x, z = int(round(cx + 44 * math.cos(math.radians(a)))), int(round(cz + 44 * math.sin(math.radians(a))))
        for dy in range(1, 16): b.set(x, SURFACE + dy, z, 'minecraft:polished_blackstone')
        b.set(x, SURFACE + 16, z, 'minecraft:sea_lantern'); b.set(x, SURFACE + 17, z, 'minecraft:end_rod[facing=up]')
    for a in range(45, 360, 90):
        x, z = int(round(cx + 52 * math.cos(math.radians(a)))), int(round(cz + 52 * math.sin(math.radians(a))))
        for dy in range(1, 12):
            b.box(x - 1, SURFACE + dy, z - 1, x + 1, SURFACE + dy, z + 1, 'minecraft:polished_deepslate' if dy < 10 else 'minecraft:cyan_stained_glass')
        b.set(x, SURFACE + 12, z, 'minecraft:amethyst_block'); b.set(x, SURFACE + 13, z, 'minecraft:amethyst_cluster[facing=up,waterlogged=false]')
    b.notes = {'raid_den': {'x': 63, 'y': SURFACE + 4, 'z': 63}}
    return b

def safari_terrain(b, seed, radius):
    hills = noise2(seed, 18)
    return island(b, radius, heights=lambda x, z: SURFACE + int(max(0, hills(x, z) - 0.45) * 12))

def lake(b, surf, cx, cz, r, depth=3, beach='minecraft:sand'):
    for (x, z), y in list(surf.items()):
        d = math.hypot(x - cx, z - cz)
        if d <= r:
            for dy in range(0, 6): b.set(x, SURFACE + dy, z, 'minecraft:air')
            bottom = SURFACE - max(1, int(depth * (1 - (d / r) ** 2)))
            for yy in range(bottom, SURFACE + 1): b.set(x, yy, z, 'minecraft:water[level=0]')
            b.set(x, bottom - 1, z, 'minecraft:sand' if d > r - 2 else 'minecraft:clay')
            surf[(x, z)] = None
        elif d <= r + 2 and y is not None:
            b.set(x, SURFACE, z, beach)
            for dy in range(1, 5): b.set(x, SURFACE + dy, z, 'minecraft:air')
            surf[(x, z)] = SURFACE

def ranger_station(b, x0, z0, gold=False):
    """15x11 lodge: quartz walls, dark oak frame, cyan glass, flat roof deck."""
    y = SURFACE
    b.box(x0, y, z0, x0 + 14, y, z0 + 10, 'minecraft:dark_oak_planks')
    for dy in range(1, 6):
        for x in range(x0, x0 + 15):
            for z in (z0, z0 + 10): b.set(x, y + dy, z, 'minecraft:white_concrete')
        for z in range(z0, z0 + 11):
            for x in (x0, x0 + 14): b.set(x, y + dy, z, 'minecraft:white_concrete')
    for x, z in ((x0, z0), (x0 + 14, z0), (x0, z0 + 10), (x0 + 14, z0 + 10)):
        for dy in range(1, 6): b.set(x, y + dy, z, 'minecraft:dark_oak_log[axis=y]')
    for x in range(x0 + 2, x0 + 13, 3):
        for dy in (2, 3): b.set(x, y + dy, z0, 'minecraft:cyan_stained_glass'); b.set(x, y + dy, z0 + 10, 'minecraft:cyan_stained_glass')
    for dy in (1, 2, 3): b.set(x0 + 7, y + dy, z0 + 10, 'minecraft:air')
    b.box(x0 - 1, y + 6, z0 - 1, x0 + 15, y + 6, z0 + 11, 'minecraft:gold_block' if gold else 'minecraft:cyan_concrete')
    b.box(x0, y + 6, z0, x0 + 14, y + 6, z0 + 10, 'minecraft:smooth_quartz')
    b.box(x0 + 3, y + 1, z0 + 2, x0 + 11, y + 1, z0 + 2, 'minecraft:dark_oak_slab[type=top,waterlogged=false]')
    for x in (x0 + 2, x0 + 12): b.set(x, y + 5, z0 + 5, 'minecraft:lantern[hanging=true]')

def observation_tower(b, x0, z0, height=14):
    y = SURFACE
    for dy in range(1, height):
        for x, z in ((x0, z0), (x0 + 4, z0), (x0, z0 + 4), (x0 + 4, z0 + 4)): b.set(x, y + dy, z, 'minecraft:dark_oak_log[axis=y]')
    for dy in range(1, height):  # ladder on the inside of the north face
        b.set(x0 + 2, y + dy, z0 + 1, 'minecraft:ladder[facing=south,waterlogged=false]')
        b.set(x0 + 2, y + dy, z0, 'minecraft:dark_oak_planks')
    b.box(x0 - 1, y + height, z0 - 1, x0 + 5, y + height, z0 + 5, 'minecraft:dark_oak_planks')
    b.set(x0 + 2, y + height, z0 + 1, 'minecraft:ladder[facing=south,waterlogged=false]')
    for x in range(x0 - 1, x0 + 6):
        for z in (z0 - 1, z0 + 5): b.set(x, y + height + 1, z, 'minecraft:dark_oak_fence')
    for z in range(z0 - 1, z0 + 6):
        for x in (x0 - 1, x0 + 5): b.set(x, y + height + 1, z, 'minecraft:dark_oak_fence')
    b.box(x0, y + height + 4, z0, x0 + 4, y + height + 4, z0 + 4, 'minecraft:cyan_concrete')
    for x, z in ((x0, z0), (x0 + 4, z0), (x0, z0 + 4), (x0 + 4, z0 + 4)):
        for dy in (2, 3): b.set(x, y + height + dy, z, 'minecraft:dark_oak_log[axis=y]')
    b.set(x0 + 2, y + height + 3, z0 + 2, 'minecraft:lantern[hanging=true]')

def scatter(b, surf, cond, chance, fn):
    for (x, z), y in sorted(surf.items()):
        if y is not None and cond(x, z) and b.rng.random() < chance and b.get(x, y + 1, z) == 'minecraft:air':
            fn(x, y + 1, z)

def build_safari():
    b = Build('Safari', 3003); surf = safari_terrain(b, 31, 61)
    lake(b, surf, 88, 40, 13)
    flatten(b, surf, 50, 98, 77, 127); flatten(b, surf, 68, 86, 86, 100); flatten(b, surf, 35, 63, 45, 73)
    arrival(b)
    path_line(b, 63, 104, 63, 70, 1, surf); path_line(b, 63, 70, 40, 45, 1, surf); path_line(b, 63, 70, 84, 62, 1, surf)
    ranger_station(b, 70, 88)
    observation_tower(b, 38, 66)
    flowers = ['dandelion', 'poppy', 'cornflower', 'oxeye_daisy', 'azure_bluet']
    free = lambda x, z: math.hypot(x - 63.5, z - 63.5) < 55 and not (68 <= x <= 86 and 86 <= z <= 100) and not (35 <= x <= 45 and 63 <= z <= 73)
    scatter(b, surf, free, 0.012, lambda x, y, z: tree(b, x, y, z, b.rng.choice(['oak', 'oak', 'birch'])))
    scatter(b, surf, lambda x, z: free(x, z) and math.hypot(x - 30, z - 85) < 12, 0.05, lambda x, y, z: (b.set(x, y, z, 'minecraft:mossy_cobblestone'), b.set(x, y + 1, z, 'minecraft:mossy_cobblestone') if b.rng.random() < .4 else None))
    scatter(b, surf, free, 0.6, lambda x, y, z: plants(b, x, y, z, flowers))
    for a in range(0, 360, 30):  # lanterns around the lake shore
        x, z = int(round(88 + 16 * math.cos(math.radians(a)))), int(round(40 + 16 * math.sin(math.radians(a))))
        if surf.get((x, z)) is not None and b.get(x, surf[(x, z)] + 1, z) == 'minecraft:air': lamp_post(b, x, surf[(x, z)] + 1, z, 2)
    for (x, z), y in surf.items():
        if y is None and math.hypot(x - 88, z - 40) < 11 and b.rng.random() < 0.05: b.set(x, SURFACE + 1, z, 'minecraft:lily_pad')
    hedge(b, {k: v for k, v in surf.items() if v is not None}, 58)
    for x in (54, 73): lamp_post(b, x, SURFACE + 1, 100, 3)
    b.notes = {'spawn_area': 'terreno dentro da sebe (raio 56 a partir do centro x63 z63)', 'ranger_station': {'x': 77, 'y': SURFACE + 1, 'z': 93}}
    return b

# ---------------------------------------------------------------- SafariVip: 64 biome zones
# 8x8 grid of 16x16 zones, one per vanilla biome (rows north -> south). Paths of polished andesite on every
# zone border (2 wide between zones) keep the zones apart and contain water. Biomes are applied after pasting
# with /fillbiome (see biome_cells in warps.json); the blocks below only give each zone the matching terrain.
BIOME_GRID = [
    ['the_end', 'end_highlands', 'end_midlands', 'small_end_islands', 'end_barrens', 'the_void', 'deep_dark', 'dripstone_caves'],
    ['nether_wastes', 'crimson_forest', 'warped_forest', 'soul_sand_valley', 'basalt_deltas', 'lush_caves', 'stony_peaks', 'windswept_gravelly_hills'],
    ['jagged_peaks', 'frozen_peaks', 'snowy_slopes', 'grove', 'ice_spikes', 'windswept_hills', 'windswept_forest', 'stony_shore'],
    ['snowy_plains', 'snowy_taiga', 'old_growth_spruce_taiga', 'plains', 'meadow', 'taiga', 'frozen_river', 'deep_frozen_ocean'],
    ['snowy_beach', 'old_growth_pine_taiga', 'dark_forest', 'forest', 'flower_forest', 'birch_forest', 'frozen_ocean', 'deep_cold_ocean'],
    ['mushroom_fields', 'swamp', 'mangrove_swamp', 'cherry_grove', 'old_growth_birch_forest', 'river', 'cold_ocean', 'deep_ocean'],
    ['desert', 'badlands', 'eroded_badlands', 'sunflower_plains', 'savanna', 'beach', 'lukewarm_ocean', 'deep_lukewarm_ocean'],
    ['wooded_badlands', 'savanna_plateau', 'windswept_savanna', 'jungle', 'bamboo_jungle', 'sparse_jungle', 'ocean', 'warm_ocean'],
]
SNOWY = {'snowy_plains', 'snowy_taiga', 'grove', 'snowy_slopes', 'ice_spikes', 'frozen_peaks', 'jagged_peaks', 'snowy_beach',
         'frozen_river', 'frozen_ocean', 'deep_frozen_ocean', 'old_growth_spruce_taiga'}
CAVES = {'lush_caves', 'dripstone_caves', 'deep_dark'}
LEAF = '[distance=1,persistent=true,waterlogged=false]'

def zone_cells(x0, z0, margin=1):
    for z in range(z0 + margin, z0 + 16 - margin):
        for x in range(x0 + margin, x0 + 16 - margin):
            yield x, z

def zone_ground(b, x0, z0, top, sub='minecraft:dirt', depth=3, deep='minecraft:stone'):
    for x, z in zone_cells(x0, z0):
        b.set(x, SURFACE, z, top)
        for dy in range(1, depth + 1): b.set(x, SURFACE - dy, z, sub)
        for y in range(1, SURFACE - depth): b.set(x, y, z, deep)

def zone_scatter(b, x0, z0, chance, fn, margin=2):
    for x, z in zone_cells(x0, z0, margin):
        if b.get(x, SURFACE + 1, z) == 'minecraft:air' and b.rng.random() < chance: fn(x, SURFACE + 1, z)

def mound(b, x0, z0, height, body, top, roughness=0.35):
    """Hill centred in the zone; returns nothing, raises columns up to SURFACE+height."""
    n = noise2(b.rng.random(), 4)
    for x, z in zone_cells(x0, z0, 2):
        d = math.hypot(x - (x0 + 7.5), z - (z0 + 7.5)) / 6.5
        h = int(height * max(0.0, 1 - d * d) * (1 - roughness + roughness * n(x, z)))
        for dy in range(1, h + 1): b.set(x, SURFACE + dy, z, top if dy == h else body)
        if h: b.set(x, SURFACE, z, body)

def water_zone(b, x0, z0, depth, floor='minecraft:sand', area=None):
    for x, z in zone_cells(x0, z0):
        if area and not area(x - x0, z - z0): continue
        b.set(x, SURFACE - depth, z, floor)
        for y in range(SURFACE - depth + 1, SURFACE + 1): b.set(x, y, z, 'minecraft:water[level=0]')

def big_tree(b, x, y, z, kind, height):
    """Taller variants (old growth): plain trunk with a layered crown."""
    log, leaves = f'minecraft:{kind}_log[axis=y]', f'minecraft:{kind}_leaves' + LEAF
    for dy in range(height): b.set(x, y + dy, z, log)
    for dy in range(height - 4, height + 2):
        r = 2 if dy < height else 1
        for dz in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if (dx or dz or dy >= height) and abs(dx) + abs(dz) <= r + 1 and b.get(x + dx, y + dy, z + dz) == 'minecraft:air':
                    b.set(x + dx, y + dy, z + dz, leaves)

def huge_mushroom(b, x, y, z, red=True):
    for dy in range(4): b.set(x, y + dy, z, 'minecraft:mushroom_stem')
    cap = 'minecraft:red_mushroom_block' if red else 'minecraft:brown_mushroom_block'
    for dz in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dx) + abs(dz) < 4: b.set(x + dx, y + 4, z + dz, cap)

def nether_tree(b, x, y, z, kind):
    stem, wart = f'minecraft:{kind}_stem[axis=y]', 'minecraft:nether_wart_block' if kind == 'crimson' else 'minecraft:warped_wart_block'
    h = b.rng.randint(4, 6)
    for dy in range(h): b.set(x, y + dy, z, stem)
    for dy in range(h - 2, h + 1):
        for dz in range(-2, 3):
            for dx in range(-2, 3):
                if abs(dx) + abs(dz) <= 3 and b.get(x + dx, y + dy, z + dz) == 'minecraft:air':
                    b.set(x + dx, y + dy, z + dz, 'minecraft:shroomlight' if b.rng.random() < 0.08 else wart)

def cave_shell(b, x0, z0, floor, wall, roof_y=7):
    """Enclosed zone with a 2-wide southern entrance so it keeps low sky light."""
    zone_ground(b, x0, z0, floor, floor, 3, wall)
    for x, z in zone_cells(x0, z0):
        b.set(x, SURFACE + roof_y, z, wall)
        edge = x in (x0 + 1, x0 + 14) or z in (z0 + 1, z0 + 14)
        if edge and not (z == z0 + 14 and x in (x0 + 7, x0 + 8)):
            for dy in range(1, roof_y): b.set(x, SURFACE + dy, z, wall)

def lava_pool(b, x0, z0, rim='minecraft:blackstone'):
    """Central 3x3 lava pool, two deep, with a rim wall; kept >= 5 blocks from the zone border."""
    for z in range(z0 + 5, z0 + 11):
        for x in range(x0 + 5, x0 + 11):
            inner = x0 + 6 <= x <= x0 + 9 and z0 + 6 <= z <= z0 + 9
            if inner:
                b.set(x, SURFACE - 2, z, rim)
                for y in (SURFACE - 1, SURFACE): b.set(x, y, z, 'minecraft:lava[level=0]')
            else:
                b.set(x, SURFACE + 1, z, 'minecraft:polished_blackstone_wall')

def ruins(b, x, z, floor, nearby):
    for dz in range(-2, 3):
        for dx in range(-2, 3): b.set(x + dx, SURFACE, z + dz, floor)
    for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        for dy in range(1, b.rng.randint(2, 4)): b.set(x + dx, SURFACE + dy, z + dz, b.rng.choice(nearby))

def build_zone(b, biome, x0, z0):
    r, cx, cz = b.rng, x0 + 7, z0 + 7
    flowers = ['dandelion', 'poppy', 'cornflower', 'oxeye_daisy', 'azure_bluet']
    grass = lambda: zone_ground(b, x0, z0, 'minecraft:grass_block')
    trees = lambda kind, chance, h=None: zone_scatter(b, x0, z0, chance, lambda x, y, z: tree(b, x, y, z, kind, h), 3)
    plant = lambda chance, fl=flowers: zone_scatter(b, x0, z0, chance, lambda x, y, z: plants(b, x, y, z, fl), 1)
    snow = lambda: zone_scatter(b, x0, z0, 0.9, lambda x, y, z: b.set(x, y, z, 'minecraft:snow[layers=1]') if b.get(x, y - 1, z) in ('minecraft:grass_block[snowy=true]', 'minecraft:snow_block') else None, 1)
    if biome in ('plains', 'meadow', 'sunflower_plains', 'forest', 'flower_forest', 'birch_forest', 'old_growth_birch_forest', 'cherry_grove', 'dark_forest'):
        grass()
        if biome == 'plains':
            plant(0.4); trees('oak', 0.01)
            zone_scatter(b, x0, z0, 0.03, lambda x, y, z: b.set(x, y, z, 'minecraft:pumpkin'), 2)
            for x, z in ((x0 + 3, z0 + 3), (x0 + 12, z0 + 12)):  # lightning rods on short stone posts
                b.set(x, SURFACE + 1, z, 'minecraft:cobblestone'); b.set(x, SURFACE + 2, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
        elif biome == 'meadow':
            plant(0.6, ['allium', 'azure_bluet', 'cornflower', 'oxeye_daisy', 'dandelion'])
            sx, sz = x0 + 4, z0 + 4
            for dy in range(5): b.set(sx, SURFACE + 1 + dy, sz, 'cobblemon:saccharine_log[axis=y]')
            for dz in range(-2, 3):
                for dx in range(-2, 3):
                    for dy in (4, 5, 6):
                        if abs(dx) + abs(dz) <= 3 and b.get(sx + dx, SURFACE + dy, sz + dz) == 'minecraft:air':
                            b.set(sx + dx, SURFACE + dy, sz + dz, 'cobblemon:saccharine_leaves[age=0,distance=1,persistent=true,waterlogged=false]')
            b.set(x0 + 11, SURFACE + 1, z0 + 11, 'minecraft:oak_planks'); b.set(x0 + 11, SURFACE + 2, z0 + 11, 'minecraft:cake[bites=0]')
        elif biome == 'sunflower_plains':
            plant(0.3)
            zone_scatter(b, x0, z0, 0.18, lambda x, y, z: (b.set(x, y, z, 'minecraft:sunflower[half=lower]'), b.set(x, y + 1, z, 'minecraft:sunflower[half=upper]')), 1)
        elif biome == 'forest': trees('oak', 0.05); trees('birch', 0.02); plant(0.3)
        elif biome == 'flower_forest':
            colours = ['poppy', 'red_tulip', 'orange_tulip', 'torchflower', 'dandelion', 'white_tulip', 'lily_of_the_valley', 'pink_tulip', 'cornflower', 'blue_orchid', 'allium', 'oxeye_daisy']
            zone_scatter(b, x0, z0, 0.7, lambda x, y, z: b.set(x, y, z, 'minecraft:' + r.choice(colours)), 1); trees('oak', 0.015)
        elif biome == 'birch_forest':
            trees('birch', 0.06); plant(0.3)
            for x, z, berry in ((x0 + 3, z0 + 12, 'oran'), (x0 + 5, z0 + 12, 'pecha'), (x0 + 7, z0 + 12, 'cheri')):
                b.set(x, SURFACE + 1, z, f'cobblemon:{berry}_berry[age=3,rooted=false]')
        elif biome == 'old_growth_birch_forest': zone_scatter(b, x0, z0, 0.05, lambda x, y, z: big_tree(b, x, y, z, 'birch', 9), 3); plant(0.3)
        elif biome == 'cherry_grove':
            trees('cherry', 0.03, 5)
            zone_scatter(b, x0, z0, 0.4, lambda x, y, z: b.set(x, y, z, 'minecraft:pink_petals[facing=north,flower_amount=4]') if on_ground(b, x, y, z) else None, 1)
        elif biome == 'dark_forest':
            water_zone(b, x0, z0, 2, 'minecraft:clay', lambda dx, dz: 9 <= dx <= 12 and 9 <= dz <= 12)
            trees('dark_oak', 0.08, 6)
            zone_scatter(b, x0, z0, 0.015, lambda x, y, z: huge_mushroom(b, x, y, z, r.random() < 0.5), 3)
    elif biome in ('taiga', 'old_growth_pine_taiga', 'old_growth_spruce_taiga', 'snowy_taiga', 'grove'):
        top = 'minecraft:grass_block[snowy=true]' if biome in SNOWY else 'minecraft:podzol' if biome.startswith('old_growth') else 'minecraft:grass_block'
        zone_ground(b, x0, z0, top)
        if biome == 'grove': mound(b, x0, z0, 5, 'minecraft:snow_block', 'minecraft:snow_block')
        zone_scatter(b, x0, z0, 0.06, lambda x, y, z: tree(b, x, y, z, 'spruce', 9 if biome.startswith('old_growth') else r.randint(6, 8)) if b.get(x, y - 1, z) != 'minecraft:snow_block' else None, 3)
        zone_scatter(b, x0, z0, 0.2, lambda x, y, z: b.set(x, y, z, 'minecraft:fern') if b.get(x, y - 1, z) in ('minecraft:grass_block', 'minecraft:podzol') else None, 1)
        if biome == 'taiga': zone_scatter(b, x0, z0, 0.03, lambda x, y, z: b.set(x, y, z, 'minecraft:pumpkin') if b.get(x, y - 1, z) == 'minecraft:grass_block' else None, 2)
        if biome == 'grove':  # small concrete ice sculpture: ice-urban spawns need concrete near natural ground
            for dy in (1, 2): b.set(x0 + 2, SURFACE + dy, z0 + 2, 'minecraft:white_concrete')
            b.set(x0 + 2, SURFACE + 3, z0 + 2, 'minecraft:light_blue_concrete')
        if biome == 'old_growth_spruce_taiga' or biome == 'old_growth_pine_taiga':
            zone_scatter(b, x0, z0, 0.02, lambda x, y, z: b.set(x, y, z, 'minecraft:mossy_cobblestone'), 2)
        if biome in SNOWY: snow()
    elif biome in ('snowy_plains', 'snowy_slopes', 'ice_spikes', 'frozen_peaks', 'jagged_peaks'):
        zone_ground(b, x0, z0, 'minecraft:grass_block[snowy=true]' if biome == 'snowy_plains' else 'minecraft:snow_block')
        if biome == 'snowy_slopes': mound(b, x0, z0, 7, 'minecraft:snow_block', 'minecraft:snow_block')
        if biome == 'frozen_peaks': mound(b, x0, z0, 10, 'minecraft:packed_ice', 'minecraft:snow_block')
        if biome == 'jagged_peaks': mound(b, x0, z0, 12, 'minecraft:stone', 'minecraft:snow_block', 0.6)
        if biome == 'ice_spikes':
            for _ in range(6):
                x, z = r.randint(x0 + 3, x0 + 12), r.randint(z0 + 3, z0 + 12); h = r.randint(4, 11)
                for dy in range(1, h + 1): b.set(x, SURFACE + dy, z, 'minecraft:packed_ice')
                if h > 6:
                    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        for dy in range(1, h // 2): b.set(x + dx, SURFACE + dy, z + dz, 'minecraft:packed_ice')
        snow()
    elif biome in ('stony_peaks', 'windswept_hills', 'windswept_forest', 'windswept_gravelly_hills'):
        zone_ground(b, x0, z0, 'minecraft:gravel' if biome == 'windswept_gravelly_hills' else 'minecraft:grass_block')
        if biome == 'stony_peaks':
            mound(b, x0, z0, 10, 'minecraft:stone', 'minecraft:calcite', 0.5)
            for x, z in ((x0 + 3, z0 + 12), (x0 + 12, z0 + 3)): b.set(x, SURFACE, z, 'minecraft:iron_ore')
        if biome == 'windswept_hills':
            mound(b, x0, z0, 5, 'minecraft:stone', 'minecraft:stone')
            ruins(b, x0 + 11, z0 + 11, 'minecraft:stone_bricks', ['minecraft:cracked_stone_bricks', 'minecraft:mossy_stone_bricks'])
            for z in range(z0 + 2, z0 + 8): b.set(x0 + 3, SURFACE + 1, z, 'minecraft:rail[shape=north_south,waterlogged=false]')
            b.set(x0 + 2, SURFACE, z0 + 4, 'minecraft:coal_ore'); b.set(x0 + 4, SURFACE, z0 + 6, 'minecraft:coal_ore')
            plant(0.2)
        if biome == 'windswept_forest': mound(b, x0, z0, 4, 'minecraft:stone', 'minecraft:grass_block'); trees('spruce', 0.05, 7); trees('oak', 0.02)
        if biome == 'windswept_gravelly_hills':
            mound(b, x0, z0, 4, 'minecraft:stone', 'minecraft:gravel')
            for x, z in ((x0 + 3, z0 + 3), (x0 + 12, z0 + 12), (x0 + 3, z0 + 12)): b.set(x, SURFACE, z, 'minecraft:redstone_ore[lit=false]')
    elif biome in ('desert', 'badlands', 'eroded_badlands', 'wooded_badlands'):
        if biome == 'desert':
            zone_ground(b, x0, z0, 'minecraft:sand', 'minecraft:sandstone')
            ruins(b, x0 + 10, z0 + 10, 'minecraft:sandstone', ['minecraft:chiseled_sandstone', 'minecraft:orange_terracotta', 'minecraft:cut_sandstone'])
            sx, sz = x0 + 3, z0 + 9  # roofed shrine: covered sand floor beside pyramid blocks
            for z in range(sz, sz + 5):
                for x in range(sx, sx + 5):
                    wall = x in (sx, sx + 4) or z in (sz, sz + 4)
                    b.set(x, SURFACE + 4, z, 'minecraft:cut_sandstone')
                    if wall and not (z == sz and x == sx + 2):
                        for dy in (1, 2, 3): b.set(x, SURFACE + dy, z, 'minecraft:chiseled_sandstone' if dy == 2 else 'minecraft:sandstone')
            b.set(sx + 2, SURFACE + 1, sz + 3, 'minecraft:orange_terracotta')
            for x, z in ((x0 + 3, z0 + 3), (x0 + 4, z0 + 9), (x0 + 9, z0 + 4)):
                for dy in range(1, 3): b.set(x, SURFACE + dy, z, 'minecraft:cactus[age=0]')
            zone_scatter(b, x0, z0, 0.05, lambda x, y, z: b.set(x, y, z, 'minecraft:dead_bush') if b.get(x, y - 1, z) == 'minecraft:sand' else None, 1)
        else:
            zone_ground(b, x0, z0, 'minecraft:red_sand' if biome != 'wooded_badlands' else 'minecraft:coarse_dirt', 'minecraft:terracotta')
            bands = ['minecraft:terracotta', 'minecraft:orange_terracotta', 'minecraft:yellow_terracotta', 'minecraft:brown_terracotta', 'minecraft:red_terracotta', 'minecraft:white_terracotta']
            if biome == 'badlands': mound(b, x0, z0, 6, 'minecraft:orange_terracotta', 'minecraft:red_sand')
            if biome == 'eroded_badlands':
                for _ in range(5):
                    x, z = r.randint(x0 + 3, x0 + 12), r.randint(z0 + 3, z0 + 12)
                    for dy in range(1, r.randint(5, 12)): b.set(x, SURFACE + dy, z, bands[dy % len(bands)])
            if biome == 'wooded_badlands':
                mound(b, x0, z0, 5, 'minecraft:terracotta', 'minecraft:grass_block'); trees('oak', 0.03, 5)
            zone_scatter(b, x0, z0, 0.04, lambda x, y, z: b.set(x, y, z, 'minecraft:dead_bush') if b.get(x, y - 1, z) == 'minecraft:red_sand' else None, 1)
    elif biome in ('savanna', 'savanna_plateau', 'windswept_savanna'):
        grass()
        if biome == 'savanna_plateau': mound(b, x0, z0, 5, 'minecraft:dirt', 'minecraft:grass_block', 0.1)
        if biome == 'windswept_savanna': mound(b, x0, z0, 6, 'minecraft:stone', 'minecraft:coarse_dirt', 0.6)
        trees('acacia', 0.03, 5); plant(0.35, ['dandelion', 'poppy'])
    elif biome in ('jungle', 'sparse_jungle', 'bamboo_jungle'):
        zone_ground(b, x0, z0, 'minecraft:podzol' if biome == 'bamboo_jungle' else 'minecraft:grass_block')
        if biome == 'bamboo_jungle':
            zone_scatter(b, x0, z0, 0.25, lambda x, y, z: [b.set(x, y + dy, z, 'minecraft:bamboo[age=0,leaves=large,stage=0]') for dy in range(r.randint(4, 9))], 2)
        else:
            trees('jungle', 0.06 if biome == 'jungle' else 0.02, 9 if biome == 'jungle' else 6)
            if biome == 'jungle':
                ruins(b, x0 + 4, z0 + 4, 'minecraft:mossy_cobblestone', ['minecraft:chiseled_stone_bricks', 'minecraft:mossy_cobblestone'])
                for x, z in ((x0 + 3, z0 + 3), (x0 + 5, z0 + 5)): b.set(x, SURFACE, z, 'minecraft:cobblestone')
        plant(0.4, ['poppy', 'dandelion'])
    elif biome == 'mushroom_fields':
        zone_ground(b, x0, z0, 'minecraft:mycelium')
        zone_scatter(b, x0, z0, 0.02, lambda x, y, z: huge_mushroom(b, x, y, z, r.random() < 0.5), 3)
        zone_scatter(b, x0, z0, 0.08, lambda x, y, z: b.set(x, y, z, r.choice(['minecraft:red_mushroom', 'minecraft:brown_mushroom'])), 1)
    elif biome in ('swamp', 'mangrove_swamp'):
        zone_ground(b, x0, z0, 'minecraft:grass_block' if biome == 'swamp' else 'minecraft:mud', 'minecraft:mud')
        pools = noise2(r.random(), 4)
        water_zone(b, x0, z0, 2, 'minecraft:mud', lambda dx, dz: 2 <= dx <= 13 and 2 <= dz <= 13 and pools(x0 + dx, z0 + dz) > 0.5)
        if biome == 'swamp': trees('oak', 0.03, 5)
        else:
            def mangrove(x, y, z):
                if b.get(x, y - 1, z) == 'minecraft:water[level=0]': return
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)): b.set(x + dx, y, z + dz, 'minecraft:mangrove_roots[waterlogged=false]')
                for dy in range(1, 6): b.set(x, y + dy, z, 'minecraft:mangrove_log[axis=y]')
                for dz in range(-2, 3):
                    for dx in range(-2, 3):
                        for dy in (5, 6):
                            if abs(dx) + abs(dz) <= 3 and b.get(x + dx, y + dy, z + dz) == 'minecraft:air': b.set(x + dx, y + dy, z + dz, 'minecraft:mangrove_leaves' + LEAF)
            zone_scatter(b, x0, z0, 0.03, mangrove, 3)
        for x, z in zone_cells(x0, z0):
            if b.get(x, SURFACE, z).startswith('minecraft:water') and r.random() < 0.15: b.set(x, SURFACE + 1, z, 'minecraft:lily_pad')
    elif biome in ('ocean', 'deep_ocean', 'warm_ocean', 'lukewarm_ocean', 'deep_lukewarm_ocean', 'cold_ocean', 'deep_cold_ocean', 'frozen_ocean', 'deep_frozen_ocean'):
        deep = biome.startswith('deep')
        floor = 'minecraft:sand' if 'warm' in biome or biome.endswith('lukewarm_ocean') else 'minecraft:gravel'
        water_zone(b, x0, z0, 12 if deep else 6, floor)
        bottom = SURFACE - (12 if deep else 6)
        if biome == 'warm_ocean':
            for x, z in zone_cells(x0, z0, 2):
                if r.random() < 0.25: b.set(x, bottom + 1, z, 'minecraft:' + r.choice(['tube', 'brain', 'bubble', 'fire', 'horn']) + '_coral_block')
        if 'warm' in biome or 'lukewarm' in biome or biome in ('ocean', 'deep_ocean'):
            for x, z in zone_cells(x0, z0, 2):
                if b.get(x, bottom + 1, z).startswith('minecraft:water') and r.random() < 0.3: b.set(x, bottom + 1, z, 'minecraft:seagrass')
        if biome in ('ocean', 'deep_ocean', 'cold_ocean', 'deep_cold_ocean', 'lukewarm_ocean', 'deep_lukewarm_ocean'):
            for x, z in zone_cells(x0, z0, 3):
                if r.random() < 0.08 and b.get(x, bottom + 1, z) == 'minecraft:water[level=0]':
                    top = SURFACE - 2
                    for y in range(bottom + 1, top): b.set(x, y, z, 'minecraft:kelp_plant')
                    b.set(x, top, z, 'minecraft:kelp[age=20]')
        if 'frozen' in biome:
            for x, z in zone_cells(x0, z0):
                if r.random() < 0.45: b.set(x, SURFACE, z, 'minecraft:packed_ice')
    elif biome in ('river', 'frozen_river', 'beach', 'snowy_beach', 'stony_shore'):
        land = {'river': 'minecraft:grass_block', 'frozen_river': 'minecraft:grass_block[snowy=true]', 'beach': 'minecraft:sand',
                'snowy_beach': 'minecraft:sand', 'stony_shore': 'minecraft:stone'}[biome]
        zone_ground(b, x0, z0, land, 'minecraft:sand' if 'beach' in biome else 'minecraft:dirt')
        channel = (lambda dx, dz: 5 <= dx <= 10) if 'river' in biome else (lambda dx, dz: dz >= 8)
        water_zone(b, x0, z0, 3 if 'river' in biome else 4, 'minecraft:sand', channel)
        if biome == 'frozen_river':
            for x, z in zone_cells(x0, z0):
                if b.get(x, SURFACE, z).startswith('minecraft:water') and r.random() < 0.5: b.set(x, SURFACE, z, 'minecraft:ice')
            snow()
        if biome == 'snowy_beach':
            zone_scatter(b, x0, z0, 0.9, lambda x, y, z: b.set(x, y, z, 'minecraft:snow[layers=1]') if b.get(x, y - 1, z) == 'minecraft:sand' else None, 1)
        if biome == 'beach':
            for x, z in ((x0 + 4, z0 + 4), (x0 + 10, z0 + 3)):
                b.set(x, SURFACE, z, 'minecraft:grass_block'); tree(b, x, SURFACE + 1, z, 'jungle', 6)
        if biome in ('river', 'beach'):  # sugar cane needs water right beside its base
            for x, z in zone_cells(x0, z0):
                if b.get(x, SURFACE, z) in ('minecraft:sand', 'minecraft:grass_block') and r.random() < 0.35 and any(
                        b.get(x + dx, SURFACE, z + dz).startswith('minecraft:water') for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    for dy in (1, 2): b.set(x, SURFACE + dy, z, 'minecraft:sugar_cane[age=0]')
            if biome == 'river': plant(0.25)
    elif biome in CAVES:
        if biome == 'lush_caves':
            cave_shell(b, x0, z0, 'minecraft:moss_block', 'minecraft:stone')
            water_zone(b, x0, z0, 2, 'minecraft:clay', lambda dx, dz: 9 <= dx <= 12 and 3 <= dz <= 6)
            zone_scatter(b, x0, z0, 0.12, lambda x, y, z: b.set(x, y, z, r.choice(['minecraft:azalea', 'minecraft:flowering_azalea', 'minecraft:moss_carpet', 'minecraft:big_dripleaf[facing=north,tilt=none,waterlogged=false]'])) if b.get(x, y - 1, z) == 'minecraft:moss_block' else None, 2)
            for x, z in ((x0 + 4, z0 + 4), (x0 + 11, z0 + 11)): b.set(x, SURFACE + 7, z, 'minecraft:glowstone')
        elif biome == 'dripstone_caves':
            cave_shell(b, x0, z0, 'minecraft:dripstone_block', 'minecraft:stone')
            zone_scatter(b, x0, z0, 0.08, lambda x, y, z: b.set(x, y, z, 'minecraft:pointed_dripstone[thickness=tip,vertical_direction=up,waterlogged=false]'), 2)
            for x, z, ore in ((x0 + 3, z0 + 3, 'iron_ore'), (x0 + 12, z0 + 4, 'copper_ore'), (x0 + 4, z0 + 11, 'redstone_ore[lit=false]'), (x0 + 11, z0 + 11, 'coal_ore')):
                b.set(x, SURFACE, z, 'minecraft:' + ore)
            for z in range(z0 + 4, z0 + 11): b.set(x0 + 7, SURFACE + 1, z, 'minecraft:rail[shape=north_south,waterlogged=false]')
            ruins(b, x0 + 11, z0 + 8, 'minecraft:stone_bricks', ['minecraft:cracked_stone_bricks', 'minecraft:mossy_stone_bricks'])
            b.set(x0 + 3, SURFACE, z0 + 8, 'minecraft:diamond_ore')
        else:
            cave_shell(b, x0, z0, 'minecraft:sculk', 'minecraft:deepslate')
            for x, z in zone_cells(x0, z0, 2):
                if r.random() < 0.4: b.set(x, SURFACE, z, 'minecraft:deepslate')
    elif biome in ('nether_wastes', 'crimson_forest', 'warped_forest', 'soul_sand_valley', 'basalt_deltas'):
        top = {'nether_wastes': 'minecraft:netherrack', 'crimson_forest': 'minecraft:crimson_nylium', 'warped_forest': 'minecraft:warped_nylium',
               'soul_sand_valley': 'minecraft:soul_soil', 'basalt_deltas': 'minecraft:basalt[axis=y]'}[biome]
        zone_ground(b, x0, z0, top, 'minecraft:netherrack', 3, 'minecraft:netherrack')
        if biome == 'nether_wastes':
            for x, z in zone_cells(x0, z0, 2):
                if r.random() < 0.06: b.set(x, SURFACE, z, r.choice(['minecraft:nether_quartz_ore', 'minecraft:nether_gold_ore']))
            lava_pool(b, x0, z0)
        if biome in ('crimson_forest', 'warped_forest'):
            kind = biome.split('_')[0]
            zone_scatter(b, x0, z0, 0.025, lambda x, y, z: nether_tree(b, x, y, z, kind) if not (5 <= x - x0 <= 10 and 5 <= z - z0 <= 10) else None, 3)
            zone_scatter(b, x0, z0, 0.15, lambda x, y, z: b.set(x, y, z, f'minecraft:{kind}_roots' if r.random() < 0.7 else f'minecraft:{kind}_fungus') if b.get(x, y - 1, z) == top else None, 1)
        if biome == 'soul_sand_valley':
            for x, z in zone_cells(x0, z0, 2):
                if r.random() < 0.4: b.set(x, SURFACE, z, 'minecraft:soul_sand')
            for x, z in ((x0 + 4, z0 + 4), (x0 + 11, z0 + 10)):
                for dy in range(1, 5): b.set(x, SURFACE + dy, z, 'minecraft:bone_block[axis=y]')
                b.set(x + 1, SURFACE + 4, z, 'minecraft:bone_block[axis=x]')
            for dy in range(1, 7): b.set(x0 + 11, SURFACE + dy, z0 + 3, 'minecraft:basalt[axis=y]')
        if biome == 'basalt_deltas':
            for x, z in zone_cells(x0, z0, 2):
                if r.random() < 0.3: b.set(x, SURFACE, z, r.choice(['minecraft:blackstone', 'minecraft:magma_block']))
            lava_pool(b, x0, z0, 'minecraft:basalt[axis=y]')
    elif biome in ('the_end', 'end_highlands', 'end_midlands', 'small_end_islands', 'end_barrens', 'the_void'):
        zone_ground(b, x0, z0, 'minecraft:end_stone', 'minecraft:end_stone', 3, 'minecraft:end_stone')
        if biome == 'end_highlands': mound(b, x0, z0, 7, 'minecraft:end_stone', 'minecraft:end_stone', 0.5)
        if biome == 'the_end':
            for dy in range(1, 10): b.box(cx, SURFACE + dy, cz, cx + 1, SURFACE + dy, cz + 1, 'minecraft:obsidian')
            b.set(cx, SURFACE + 10, cz, 'minecraft:end_rod[facing=up]')
        if biome == 'small_end_islands':
            for x, z in zone_cells(x0, z0):
                if math.hypot(x - cx - 0.5, z - cz - 0.5) > 4.5: b.set(x, SURFACE, z, 'minecraft:end_stone')
            for dx, dz, h in ((-4, -4, 3), (4, 3, 5), (-3, 4, 4)):
                b.box(cx + dx - 1, SURFACE + h, cz + dz - 1, cx + dx + 1, SURFACE + h, cz + dz + 1, 'minecraft:end_stone')
        if biome == 'the_void':
            for x, z in zone_cells(x0, z0): b.set(x, SURFACE, z, 'minecraft:obsidian' if (x + z) % 2 else 'minecraft:end_stone')
        if biome in ('end_midlands', 'end_barrens', 'end_highlands'):
            zone_scatter(b, x0, z0, 0.03, lambda x, y, z: [b.set(x, y + dy, z, 'minecraft:purpur_pillar[axis=y]') for dy in range(r.randint(1, 3))] if b.get(x, y - 1, z) == 'minecraft:end_stone' else None, 2)
            zone_scatter(b, x0, z0, 0.03, lambda x, y, z: b.set(x, y, z, 'minecraft:chorus_flower[age=5]') if b.get(x, y - 1, z) == 'minecraft:end_stone' else None, 2)
    else:
        raise ValueError(biome)

def zone_inventory(b, cell):
    """What a zone offers to spawn rules: blocks present, fluids and open/covered ground spots."""
    (x0, _, z0), (x1, _, z1) = cell['from'], cell['to']
    blocks, water, lava, open_sky, covered = set(), False, False, False, False
    for z in range(z0 + 1, z1):
        for x in range(x0 + 1, x1):
            column = [b.get(x, y, z) for y in range(HEIGHT)]
            for blk in column:
                if blk != 'minecraft:air': blocks.add(blk.split('[')[0])
            water |= any(c.startswith('minecraft:water') for c in column)
            for y in range(HEIGHT - 1):  # water surface under open sky, or under ice/roof
                if column[y].startswith('minecraft:water') and not column[y + 1].startswith('minecraft:water'):
                    above = any(c != 'minecraft:air' for c in column[y + 1:])
                    covered |= above; open_sky |= not above
            lava |= any(c.startswith('minecraft:lava') for c in column)
            for y in range(1, HEIGHT - 2):
                if column[y] != 'minecraft:air' and not column[y].startswith(('minecraft:water', 'minecraft:lava')) and column[y + 1] == 'minecraft:air' and column[y + 2] == 'minecraft:air':
                    above = any(c != 'minecraft:air' for c in column[y + 3:])
                    covered |= above; open_sky |= not above
    return {'biome': cell['biome'], 'blocks': sorted(blocks), 'water': water, 'lava': lava, 'open_sky': open_sky, 'covered': covered}

def build_safari_vip():
    b = Build('SafariVip', 4004)
    # Square slab island: stone body, rough underside, polished andesite paths on every zone border.
    under = noise2(5, 9)
    for z in range(SIZE):
        for x in range(SIZE):
            bottom = 1 + int(under(x, z) * 3)
            for y in range(bottom, SURFACE): b.set(x, y, z, 'minecraft:stone')
            if x % 16 in (0, 15) or z % 16 in (0, 15): b.set(x, SURFACE, z, 'minecraft:polished_andesite')
    cells = []
    for row, names in enumerate(BIOME_GRID):
        for col, biome in enumerate(names):
            x0, z0 = col * 16, row * 16
            build_zone(b, biome, x0, z0)
            cells.append({'biome': 'minecraft:' + biome, 'from': [x0, 0, z0], 'to': [x0 + 15, HEIGHT - 1, z0 + 15]})
    # Central VIP lodge and urban plaza (concrete only here, >= 5 blocks from the wild interiors of other zones).
    for z in range(54, 74):
        for x in range(54, 74):
            for y in range(SURFACE + 1, HEIGHT): b.set(x, y, z, 'minecraft:air')
            b.set(x, SURFACE, z, 'minecraft:white_concrete' if (x + z) % 2 else 'minecraft:cyan_concrete')
    for z in range(58, 70):
        for x in range(58, 70):
            wall = x in (58, 69) or z in (58, 69)
            b.set(x, SURFACE, z, 'minecraft:smooth_quartz')
            if wall:
                for dy in range(1, 6): b.set(x, SURFACE + dy, z, 'minecraft:quartz_bricks')
            b.set(x, SURFACE + 6, z, 'minecraft:gold_block' if wall else 'minecraft:smooth_quartz')
    for x in (60, 63, 64, 67):
        for dy in (2, 3): b.set(x, SURFACE + dy, 58, 'minecraft:cyan_stained_glass'); b.set(x, SURFACE + dy, 69, 'minecraft:cyan_stained_glass')
    for x in (63, 64):
        for dy in (1, 2, 3): b.set(x, SURFACE + dy, 69, 'minecraft:air')
    for x in (60, 66):
        b.set(x, SURFACE + 1, 60, 'cobblemon:pc[facing=south,on=false,part=bottom]'); b.set(x, SURFACE + 2, 60, 'cobblemon:pc[facing=south,on=false,part=top]')
    b.set(63, SURFACE + 5, 63, 'minecraft:lantern[hanging=true]')
    for x, z in ((55, 55), (72, 55), (55, 72), (72, 72)):
        b.set(x, SURFACE + 1, z, 'minecraft:quartz_pillar[axis=y]'); b.set(x, SURFACE + 2, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    b.set(71, SURFACE + 1, 63, 'minecraft:dark_oak_planks'); b.set(71, SURFACE + 2, 63, 'minecraft:cake[bites=0]')
    # Paths from the plaza to the arrival and the arrival platform (no concrete outside the plaza).
    for z in range(74, 118):
        for x in (63, 64): b.set(x, SURFACE, z, 'minecraft:polished_andesite'); [b.set(x, SURFACE + dy, z, 'minecraft:air') for dy in range(1, 8)]
    for z in range(116, 128):
        for x in range(57, 71):
            b.set(x, SURFACE, z, 'minecraft:smooth_quartz')
            for dy in range(1, 12): b.set(x, SURFACE + dy, z, 'minecraft:air')
    pokeball(b, 63, SURFACE, 121, 4, colours=('minecraft:cyan_wool', 'minecraft:white_wool'))
    b.arrival = {'x': 63, 'y': SURFACE + 1, 'z': 121, 'yaw': 180}
    # Lamp posts at path crossings, except next to snow or ice (block light would melt it).
    for row in range(1, 8):
        for col in range(1, 8):
            around = {BIOME_GRID[r][c] for r in (row - 1, row) for c in (col - 1, col)}
            if around & SNOWY or (54 <= col * 16 <= 73 and 54 <= row * 16 <= 73): continue
            lamp_post(b, col * 16 - 1 + (col % 2), SURFACE + 1, row * 16 - 1 + (row % 2), 3)
    b.notes = {'biome_cells': cells, 'paste_hint': 'superficie em Y=61 (origem Y=45) para os pés dos Pokémon ficarem em Y=62',
               'plaza': {'x': 63, 'y': SURFACE + 1, 'z': 63}}
    return b

# ---------------------------------------------------------------- preview
COLORS = [('end_stone', (222, 222, 160)), ('red_sand', (190, 100, 40)), ('netherrack', (110, 40, 40)), ('crimson', (150, 30, 40)),
          ('warped', (40, 125, 115)), ('soul', (85, 65, 50)), ('basalt', (80, 80, 88)), ('magma', (150, 70, 30)), ('lava', (230, 110, 20)),
          ('terracotta', (160, 90, 60)), ('mycelium', (115, 95, 115)), ('podzol', (100, 70, 40)), ('mud', (60, 50, 45)),
          ('packed_ice', (150, 180, 230)), ('ice', (170, 200, 240)), ('calcite', (220, 220, 215)), ('gravel', (130, 125, 120)),
          ('obsidian', (25, 18, 35)), ('purpur', (170, 120, 170)), ('sculk', (20, 45, 55)), ('bamboo', (120, 170, 60)),
          ('pumpkin', (220, 130, 30)), ('kelp', (40, 110, 50)), ('coral', (230, 90, 140)), ('dripstone', (130, 100, 80)),
          ('water', (52, 112, 200)), ('cyan_stained_glass', (70, 180, 200)), ('cyan', (22, 140, 152)), ('gold', (230, 190, 50)),
          ('quartz', (235, 230, 222)), ('white_concrete', (225, 228, 230)), ('sea_lantern', (200, 235, 230)), ('lantern', (255, 200, 90)),
          ('blackstone', (45, 40, 48)), ('deepslate', (70, 70, 76)), ('amethyst', (150, 100, 200)), ('cherry_leaves', (240, 170, 200)),
          ('spruce_leaves', (50, 90, 60)), ('birch_leaves', (110, 160, 80)), ('azalea_leaves', (90, 140, 60)), ('leaves', (60, 130, 50)),
          ('snow', (245, 248, 252)), ('sand', (220, 205, 150)), ('dirt_path', (150, 120, 80)), ('coarse_dirt', (110, 80, 55)),
          ('moss', (90, 120, 50)), ('mossy', (100, 115, 95)), ('dark_oak', (70, 50, 35)), ('log', (100, 80, 50)),
          ('grass_block', (95, 160, 70)), ('short_grass', (95, 170, 70)), ('tall_grass', (95, 170, 70)), ('lily', (40, 120, 40)),
          ('tuff', (110, 110, 100)), ('andesite', (135, 135, 135)), ('stone', (125, 125, 125)), ('cobblestone', (120, 120, 120))]
FLOWERS = ('poppy', 'dandelion', 'cornflower', 'oxeye', 'bluet', 'allium', 'tulip', 'lily_of_the_valley')

def color(block):
    block = block.split('[')[0]  # properties such as waterlogged=false must not match "water"
    if any(f in block for f in FLOWERS): return (230, 120, 140)
    for key, rgb in COLORS:
        if key in block: return rgb
    return (160, 160, 160)

def preview(b, path, scale=4):
    rows = []
    for z in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            rgb, top = (18, 22, 30), None
            for y in range(HEIGHT - 1, -1, -1):
                blk = b.get(x, y, z)
                if blk != 'minecraft:air': rgb, top = color(blk), y; break
            if top is not None:
                shade = 0.75 + 0.5 * (top / HEIGHT); rgb = tuple(min(255, int(c * shade)) for c in rgb)
            row += bytes(rgb) * scale
        for _ in range(scale): rows.append(b'\x00' + bytes(row))
    w = h = SIZE * scale
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
    path.write_bytes(png)

def biome_commands(cells, ox, oy, oz):
    """Absolute /fillbiome commands for the SafariVip zones pasted with its origin at (ox, oy, oz)."""
    return [f"fillbiome {ox + c['from'][0]} {oy + c['from'][1]} {oz + c['from'][2]} {ox + c['to'][0]} {oy + c['to'][1]} {oz + c['to'][2]} {c['biome']}"
            for c in cells]

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('out')
    parser.add_argument('--safarivip-origin', nargs=3, type=int, metavar=('X', 'Y', 'Z'), help='also write absolute /fillbiome commands')
    args = parser.parse_args()
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True); summary = {}
    for build in (build_vip, build_raid, build_safari, build_safari_vip):
        b = build()
        (out / f'atlas-warp-{b.name.lower()}.litematic').write_bytes(b.litematic())
        preview(b, out / f'atlas-warp-{b.name.lower()}-preview.png')
        summary[b.name] = {'file': f'atlas-warp-{b.name.lower()}.litematic', 'size': [SIZE, HEIGHT, SIZE],
                           'arrival': b.arrival, 'palette': len(b.palette), 'blocks': sum(1 for v in b.cells if v), 'notes': b.notes}
        summary[b.name]['water_leaks'] = water_leaks(b)
        if b.name == 'SafariVip':
            (out / 'safarivip-zones.json').write_text(json.dumps([zone_inventory(b, c) for c in b.notes['biome_cells']], indent=1) + '\n')
            if args.safarivip_origin:
                (out / 'safarivip-fillbiome.txt').write_text('\n'.join(biome_commands(b.notes['biome_cells'], *args.safarivip_origin)) + '\n')
        print(b.name, summary[b.name]['blocks'], 'blocos,', len(b.palette), 'tipos, vazamentos de água:', summary[b.name]['water_leaks'])
    (out / 'warps.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main()
