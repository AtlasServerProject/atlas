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

def pokeball(b, cx, y, cz, r):
    """Floor emblem in Atlas colours: cyan top, white bottom, dark band and button."""
    for z in range(cz - r, cz + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x - cx, z - cz)
            if d > r + 0.3: continue
            if d > r - 0.9: block = 'minecraft:polished_blackstone'
            elif d <= r * 0.22: block = 'minecraft:white_concrete' if d <= r * 0.12 else 'minecraft:polished_blackstone'
            elif abs(z - cz) <= max(1, r // 6): block = 'minecraft:polished_blackstone'
            else: block = 'minecraft:cyan_concrete' if z < cz else 'minecraft:white_concrete'
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

GROUND = ('minecraft:grass_block', 'minecraft:moss_block')

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

def build_safari_vip():
    b = Build('SafariVip', 4004); surf = safari_terrain(b, 47, 62)
    lake(b, surf, 90, 40, 14, depth=4)
    flatten(b, surf, 50, 98, 77, 127); flatten(b, surf, 52, 52, 74, 70)
    for (x, z) in ((85, 37), (95, 44)):
        b.disc(x, SURFACE, z, 2.5, 'minecraft:grass_block'); b.disc(x, SURFACE - 1, z, 2.5, 'minecraft:dirt'); tree(b, x, SURFACE + 1, z, 'cherry', 5)
    arrival(b)
    path_line(b, 63, 104, 63, 74, 1, surf, 'minecraft:smooth_quartz'); path_line(b, 63, 56, 63, 30, 1, surf); path_line(b, 52, 64, 30, 64, 1, surf); path_line(b, 76, 64, 98, 64, 1, surf)
    # Central VIP lodge with gold trim and a roof deck.
    ranger_station(b, 56, 56, gold=True)
    pokeball(b, 63, SURFACE + 6, 61, 4)
    quadrant = lambda x, z: ('nw' if x < 64 else 'ne') if z < 64 else ('sw' if x < 64 else 'se')
    inside = lambda x, z: math.hypot(x - 63.5, z - 63.5) < 56 and not (53 <= x <= 73 and 53 <= z <= 69)
    # NW: flower meadow with cherry trees.
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) == 'nw', 0.012, lambda x, y, z: tree(b, x, y, z, 'cherry', 5))
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) == 'nw', 0.7, lambda x, y, z: b.set(x, y, z, 'minecraft:' + b.rng.choice(['pink_tulip', 'allium', 'azure_bluet', 'cornflower', 'oxeye_daisy', 'lily_of_the_valley'])) if on_ground(b, x, y, z) else None)
    # SW: rocky hills with moss and boulders.
    for (x, z), y in surf.items():
        if y is not None and inside(x, z) and quadrant(x, z) == 'sw' and b.get(x, y, z) == 'minecraft:grass_block':
            b.set(x, y, z, b.rng.choice(['minecraft:stone', 'minecraft:andesite', 'minecraft:moss_block', 'minecraft:grass_block', 'minecraft:coarse_dirt']))
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) == 'sw', 0.03, lambda x, y, z: b.box(x, y, z, x + 1, y + b.rng.randint(0, 2), z + 1, 'minecraft:mossy_cobblestone'))
    # SE: snowy taiga.
    for (x, z), y in surf.items():
        if y is not None and inside(x, z) and quadrant(x, z) == 'se' and b.get(x, y, z) == 'minecraft:grass_block':
            b.set(x, y, z, 'minecraft:grass_block[snowy=true]')
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) == 'se', 0.02, lambda x, y, z: tree(b, x, y, z, 'spruce', b.rng.randint(6, 8)))
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) == 'se', 0.95, lambda x, y, z: b.set(x, y, z, 'minecraft:snow[layers=1]') if b.get(x, y - 1, z) == 'minecraft:grass_block[snowy=true]' else None)
    # NE around the lake and remaining grass: plants.
    scatter(b, surf, lambda x, z: inside(x, z) and quadrant(x, z) in ('ne', 'nw'), 0.5, lambda x, y, z: plants(b, x, y, z, ['dandelion', 'poppy']))
    for (x, z), y in surf.items():
        if y is None and b.rng.random() < 0.06: b.set(x, SURFACE + 1, z, 'minecraft:lily_pad')
    hedge(b, {k: v for k, v in surf.items() if v is not None}, 59)
    for a in range(0, 360, 20):
        x, z = int(63.5 + 52 * math.cos(math.radians(a))), int(63.5 + 52 * math.sin(math.radians(a)))
        if (x, z) in surf and surf[(x, z)] is not None and b.get(x, surf[(x, z)] + 1, z) == 'minecraft:air': lamp_post(b, x, surf[(x, z)] + 1, z, 3)
    b.notes = {'biomes': {'nw': 'campo florido', 'ne': 'lago', 'sw': 'morros rochosos', 'se': 'taiga nevada'}, 'lodge': {'x': 63, 'y': SURFACE + 1, 'z': 61}}
    return b

# ---------------------------------------------------------------- preview
COLORS = [('water', (52, 112, 200)), ('cyan_stained_glass', (70, 180, 200)), ('cyan', (22, 140, 152)), ('gold', (230, 190, 50)),
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

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('out'); args = parser.parse_args()
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True); summary = {}
    for build in (build_vip, build_raid, build_safari, build_safari_vip):
        b = build()
        (out / f'atlas-warp-{b.name.lower()}.litematic').write_bytes(b.litematic())
        preview(b, out / f'atlas-warp-{b.name.lower()}-preview.png')
        summary[b.name] = {'file': f'atlas-warp-{b.name.lower()}.litematic', 'size': [SIZE, HEIGHT, SIZE],
                           'arrival': b.arrival, 'palette': len(b.palette), 'blocks': sum(1 for v in b.cells if v), 'notes': b.notes}
        summary[b.name]['water_leaks'] = water_leaks(b)
        print(b.name, summary[b.name]['blocks'], 'blocos,', len(b.palette), 'tipos, vazamentos de água:', summary[b.name]['water_leaks'])
    (out / 'warps.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main()
