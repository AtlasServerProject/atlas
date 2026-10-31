#!/usr/bin/env python3
"""Generate the VIP, Raid, Safari and SafariVip warp builds as Litematica schematics (+ top-down previews).

Pure Python, deterministic (fixed seeds). VIP, Raid and Safari are 128x128 floating islands, SafariVip a 192x192
round island in its own sea; all in the Atlas palette:
quartz, white/cyan concrete, dark oak, polished blackstone and sea lanterns. Output: <out>/<name>.litematic,
<name>-preview.png (top-down), <name>-view.png (from the south) and warps.json with the arrival point of each build (relative to the schematic origin).
"""
import argparse, array, collections, gzip, json, math, pathlib, random, struct, time, zlib

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
    def __init__(self, name, seed, size=SIZE):
        self.name, self.rng, self.size = name, random.Random(seed), size
        self.palette, self.index = ['minecraft:air'], {'minecraft:air': 0}
        self.cells = array.array('H', bytes(2 * size * HEIGHT * size))
        self.arrival = None
        self.notes = {}

    def id(self, block):
        if block not in self.index:
            self.index[block] = len(self.palette); self.palette.append(block)
        return self.index[block]

    def set(self, x, y, z, block):
        n = self.size
        if 0 <= x < n and 0 <= y < HEIGHT and 0 <= z < n:
            self.cells[(y * n + z) * n + x] = self.id(block)

    def get(self, x, y, z):
        n = self.size
        if 0 <= x < n and 0 <= y < HEIGHT and 0 <= z < n:
            return self.palette[self.cells[(y * n + z) * n + x]]
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
        volume = self.size * HEIGHT * self.size
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
        size = {'x': Int(self.size), 'y': Int(HEIGHT), 'z': Int(self.size)}
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
        for z in range(b.size):
            for x in range(b.size):
                if b.get(x, y, z).startswith('minecraft:water'):
                    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                        if b.get(x + dx, y + dy, z + dz) == 'minecraft:air' or not (0 <= x + dx < b.size and 0 <= z + dz < b.size and y + dy >= 0):
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
    cx = cz = 63   # whole block, so the pedestal has odd width and a true centre block
    # Arena floor with cyan rings.
    b.disc(cx, SURFACE, cz, 27, 'minecraft:polished_blackstone_bricks')
    for ring in (10.5, 18.5, 26.5): b.disc(cx, SURFACE, cz, ring, 'minecraft:cyan_concrete', inner=ring - 1)
    # Stepped pedestal; the raid den goes on the chiseled quartz at the top centre.
    for tier, rr in enumerate((7, 5, 3)):
        b.disc(cx, SURFACE + 1 + tier, cz, rr, 'minecraft:polished_deepslate')
        b.disc(cx, SURFACE + 1 + tier, cz, rr, 'minecraft:deepslate_tiles', inner=rr - 1)
    b.box(62, SURFACE + 3, 62, 64, SURFACE + 3, 64, 'minecraft:chiseled_quartz_block')
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

# ---------------------------------------------------------------- SafariVip: round island of the main overworld biomes
# A round island in a circular sea with the Atlas Pokémon Center under a glass dome in the middle and the main
# overworld biomes around it as organic sectors, laid out like a climate wheel: snowy mountain to the north, snow and
# taiga to the north-west, forests and swamp to the west, plains at the southern arrival, desert, savanna and jungle to
# the east, cherry grove and meadow under the mountain. No Nether or End biomes. Each 4x4 column gets its biome after
# pasting with /fillbiome (safarivip-biomes.json / safarivip-fillbiome.txt); the caves are 3D boxes inside the mountain.
SV, SV_C, SV_PLAZA, SV_SEA = 192, 96, 22, 93   # build size, centre, plaza radius, sea radius (barrier ring outside)
SECTORS = [  # degrees clockwise from north: from, to, inner biome, outer biome
    (130, 155, 'desert', 'badlands'), (155, 205, 'plains', 'plains'), (205, 232, 'forest', 'flower_forest'),
    (232, 256, 'birch_forest', 'swamp'), (256, 280, 'dark_forest', 'swamp'), (280, 302, 'taiga', 'snowy_taiga'),
    (302, 328, 'snowy_plains', 'ice_spikes'), (328, 385, 'mountain', 'mountain'), (25, 60, 'cherry_grove', 'meadow'),
    (60, 105, 'jungle', 'jungle'), (105, 130, 'savanna', 'savanna'),
]
PEAKS = [(352, 42, 33, 30), (18, 52, 22, 20), (330, 58, 17, 16)]   # angle, distance, height, radius
RIVER = [(34, 28), (40, 42), (47, 55), (50, 68), (56, 92)]          # (angle, distance) from the mountain to the NE sea
CAVES = {'lush_caves': (344, 38), 'dripstone_caves': (16, 46)}      # chamber centres (angle, distance)
SNOWY = {'snowy_plains', 'snowy_taiga', 'ice_spikes', 'jagged_peaks'}
BASE = {'plains': (0.2, 0.8), 'forest': (1, 1.5), 'flower_forest': (0.6, 1), 'birch_forest': (1, 1.5), 'swamp': (-0.1, 0.6),
        'dark_forest': (1.2, 1.5), 'taiga': (1.5, 2), 'snowy_taiga': (1.5, 2), 'snowy_plains': (0.8, 1.2), 'ice_spikes': (0.8, 1),
        'jagged_peaks': (2, 1), 'stony_peaks': (2, 2), 'cherry_grove': (3, 3), 'meadow': (2.5, 2), 'jungle': (1.2, 1.8),
        'savanna': (1, 1.2), 'desert': (0.6, 1.8), 'badlands': (1, 1), 'beach': (0.2, 0.3), 'river': (-2.5, 0),
        'ocean': (-6, 2), 'warm_ocean': (-5, 2)}
BANDS = ['minecraft:terracotta', 'minecraft:orange_terracotta', 'minecraft:yellow_terracotta', 'minecraft:terracotta',
         'minecraft:brown_terracotta', 'minecraft:red_terracotta', 'minecraft:white_terracotta']
LEAF = '[distance=1,persistent=true,waterlogged=false]'

def sv_xy(angle, dist):
    a = math.radians(angle); return SV_C + dist * math.sin(a), SV_C - dist * math.cos(a)

def sv_polar(x, z):
    dx, dz = x - SV_C, z - SV_C
    return math.hypot(dx, dz), math.degrees(math.atan2(dx, -dz)) % 360

def seg_dist(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az; t = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz)))
    return math.hypot(px - ax - t * vx, pz - az - t * vz)

class SafariMap:
    """Biome and height field of the island, both deterministic from the seed."""
    def __init__(self, rng):
        n = lambda scale: noise2(rng.random(), scale)
        self.warp, self.split, self.coast_n, self.rough, self.rough2 = n(22), n(12), n(14), n(6), n(3)
        self.detail, self.mesa, self.puddle, self.under = n(7), n(9), n(4), n(9)
        self.river = [sv_xy(a, d) for a, d in RIVER]
        self.peaks = [(*sv_xy(a, d), h, r) for a, d, h, r in PEAKS]

    def coast(self, x, z): return 80 + 14 * (self.coast_n(x, z) - 0.5)
    def river_dist(self, x, z): return min(seg_dist(x, z, *a, *b) for a, b in zip(self.river, self.river[1:]))

    def mountain(self, x, z):
        h = max(H * max(0.0, 1 - math.hypot(x - px, z - pz) / R) ** 1.6 for px, pz, H, R in self.peaks)
        r, _ = sv_polar(x, z)
        return h * (0.8 + 0.4 * self.rough(x, z)) * max(0.0, min(1.0, (r - 26) / 10))

    def biome(self, x, z):
        r, a = sv_polar(x, z)
        if r <= SV_PLAZA + 2: return 'plains'
        c = self.coast(x, z)
        if r > c: return 'warm_ocean' if 50 <= a <= 165 else 'ocean'
        if r > 26 and self.river_dist(x, z) < 2.6: return 'river'
        aw = (a + 26 * (self.warp(x, z) - 0.5)) % 360
        name = next(inner if r < 50 + 14 * (self.split(x, z) - 0.5) else outer
                    for lo, hi, inner, outer in SECTORS if lo <= aw < hi or lo <= aw + 360 < hi)
        if name == 'mountain': return 'jagged_peaks' if self.mountain(x, z) > 15 else 'stony_peaks'
        if r > c - 5 and 55 <= a <= 210 and name != 'badlands': return 'beach'
        return name

def build_safari_vip():
    b = Build('SafariVip', 4004, SV); m = SafariMap(b.rng)
    quart = {(qx, qz): m.biome(qx * 4 + 1.5, qz * 4 + 1.5) for qz in range(SV // 4) for qx in range(SV // 4)}
    biome_of = lambda x, z: quart[(x // 4, z // 4)]
    cols = [(x, z) for z in range(SV) for x in range(SV) if math.hypot(x - SV_C, z - SV_C) <= SV_SEA]

    # Height field: per-biome base blurred across biome borders, then mountains, mesas, river, coast and plaza.
    target = {}
    for x, z in cols:
        base, amp = BASE[biome_of(x, z)]; target[(x, z)] = base + amp * (2 * m.detail(x, z) - 1)
    surf = {}
    for x, z in cols:
        near = [target[(x + dx, z + dz)] for dz in range(-3, 4) for dx in range(-3, 4) if (x + dx, z + dz) in target]
        h, r, biome = sum(near) / len(near), math.hypot(x - SV_C, z - SV_C), biome_of(x, z)
        h += m.mountain(x, z)
        if biome == 'badlands': h += 8 if m.mesa(x, z) > 0.6 else 4 if m.mesa(x, z) > 0.52 else 0
        if biome == 'swamp' and m.puddle(x, z) > 0.56: h = -1
        rd = m.river_dist(x, z)
        if r > 26 and rd < 3.2: h = -3 if rd < 1.8 else min(h, -1)
        c = m.coast(x, z)
        if r > c: h = -min(10.0, 2 + (r - c) * 0.7) + 1.5 * (m.detail(x, z) - 0.5)
        elif r > c - 6: h = min(h, (c - r) * (3 if biome.endswith('peaks') else 0.35))
        if r < SV_PLAZA: h = 0
        elif r < SV_PLAZA + 8: h *= (r - SV_PLAZA) / 8
        surf[(x, z)] = max(3, min(HEIGHT - 8, SURFACE + round(h)))

    # Columns: rugged underside, stone body, biome soil and top, water up to sea level.
    for x, z in cols:
        y0, biome, r = surf[(x, z)], biome_of(x, z), math.hypot(x - SV_C, z - SV_C)
        bottom = max(1, min(y0 - 2, SURFACE - 5 - int(max(0.0, 1 - (r / 88) ** 2) * 9 * (0.6 + 0.4 * m.under(x, z)))))
        steep = max(abs(y0 - surf.get((x + dx, z + dz), y0)) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 3
        wet = y0 < SURFACE
        for y in range(bottom, y0 + 1):
            depth = y0 - y
            if biome == 'badlands' and y >= SURFACE - 2 and (depth or steep): blk = BANDS[y % len(BANDS)]
            elif depth >= 4: blk = b.rng.choice(['minecraft:stone'] * 7 + ['minecraft:andesite', 'minecraft:tuff', 'minecraft:deepslate'])
            elif depth: blk = soil(biome, wet, b.rng)
            else: blk = top_block(biome, y0, wet, steep, m, x, z, b.rng)
            b.set(x, y, z, blk)
        for y in range(y0 + 1, SURFACE + 1): b.set(x, y, z, 'minecraft:water[level=0]')
    for x, z in ((x, z) for z in range(SV) for x in range(SV) if SV_SEA < math.hypot(x - SV_C, z - SV_C) <= SV_SEA + 1.5):
        for y in range(SURFACE - 12, SURFACE + 1): b.set(x, y, z, 'minecraft:barrier')   # holds the sea, invisible
    blocked = set()

    plaza_and_center(b, blocked)
    caves = carve_caves(b, m, surf)
    arrival_pier(b, surf, blocked)
    for angle, reach in ((40, 62), (78, 66), (140, 60), (245, 62), (292, 60), (344, 30), (16, 38)):
        winding_path(b, surf, blocked, angle, reach)
    pikachu(b, *ground(b, surf, *map(round, sv_xy(196, 50))), blocked)
    snorlax(b, *ground(b, surf, *map(round, sv_xy(224, 64))), blocked)
    pokeball_statue(b, *map(round, sv_xy(138, 87)), blocked)
    by_biome = collections.defaultdict(list)
    for x, z in cols: by_biome[biome_of(x, z)].append((x, z))
    landmarks(b, m, surf, blocked, by_biome)
    decorate(b, surf, blocked, by_biome)
    lamps(b, surf, blocked, biome_of)

    b.arrival = {'x': SV_C, 'y': SURFACE + 1, 'z': SV_C + 72, 'yaw': 180}
    b.biome_boxes = biome_boxes(quart, caves)
    b.zones = [region_inventory(b, name, by_biome[name], caves) for name in sorted(by_biome)] + \
              [region_inventory(b, name, None, caves) for name in sorted(caves)]
    b.notes = {'paste_hint': 'origem com X e Z múltiplos de 4 e Y=45: superfície em Y=61, Pokémon em Y=62',
               'plaza': {'x': SV_C, 'y': SURFACE + 1, 'z': SV_C}, 'biomes': sorted(set(by_biome) | set(caves)),
               'fillbiome_boxes': len(b.biome_boxes)}
    return b

def soil(biome, wet, rng):
    if biome in ('desert', 'beach') or (wet and biome in ('ocean', 'warm_ocean', 'river')): return 'minecraft:sandstone' if biome == 'desert' else 'minecraft:sand'
    if biome == 'badlands': return 'minecraft:terracotta'
    if biome.endswith('peaks'): return 'minecraft:stone'
    if biome == 'ice_spikes': return 'minecraft:snow_block'
    return 'minecraft:mud' if biome == 'swamp' and wet else 'minecraft:dirt'

def top_block(biome, y, wet, steep, m, x, z, rng):
    high = y > SURFACE + 14
    if wet:
        if biome in ('ocean', 'river'): return rng.choice(['minecraft:gravel', 'minecraft:sand', 'minecraft:sand', 'minecraft:clay'])
        if biome == 'swamp': return 'minecraft:mud'
        return 'minecraft:sand'
    if biome == 'jagged_peaks': return 'minecraft:snow_block' if high or not steep else 'minecraft:stone'
    if biome == 'stony_peaks':
        if steep: return rng.choice(['minecraft:stone', 'minecraft:andesite', 'minecraft:stone'])
        return rng.choice(['minecraft:stone', 'minecraft:calcite', 'minecraft:gravel', 'minecraft:andesite', 'minecraft:grass_block'])
    if biome in ('desert', 'beach', 'warm_ocean', 'ocean'): return 'minecraft:sandstone' if steep and biome == 'desert' else 'minecraft:sand'
    if biome == 'badlands': return BANDS[y % len(BANDS)] if steep else 'minecraft:red_sand'
    if biome == 'ice_spikes': return 'minecraft:snow_block'
    if steep and y > SURFACE + 5: return 'minecraft:snow_block' if biome in SNOWY else 'minecraft:stone'
    if biome in SNOWY or high: return 'minecraft:grass_block[snowy=true]'
    if biome in ('taiga', 'dark_forest') and m.rough2(x, z) > 0.62: return 'minecraft:podzol'
    if biome == 'jungle' and m.rough2(x, z) > 0.7: return 'minecraft:podzol'
    if biome == 'swamp' and m.rough2(x, z) > 0.65: return 'minecraft:mud'
    if biome == 'savanna' and m.rough2(x, z) > 0.72: return 'minecraft:coarse_dirt'
    return 'minecraft:grass_block'

def ground(b, surf, x, z):
    return x, surf[(x, z)] + 1, z

def clear_above(b, x, y, z, height=12):
    for dy in range(height): b.set(x, y + dy, z, 'minecraft:air')

# ---- centre: Atlas Pokémon Center under a glass dome
def plaza_and_center(b, blocked):
    c, y = SV_C, SURFACE
    for z in range(c - SV_PLAZA - 1, c + SV_PLAZA + 2):
        for x in range(c - SV_PLAZA - 1, c + SV_PLAZA + 2):
            d = math.hypot(x - c, z - c)
            if d > SV_PLAZA + 0.5: continue
            clear_above(b, x, y + 1, z, 30)
            if d > SV_PLAZA - 1: blk = 'minecraft:quartz_bricks'
            elif d > 17: blk = 'minecraft:polished_andesite' if (x + z) % 2 else 'minecraft:smooth_stone'
            elif d > 16: blk = 'minecraft:chiseled_quartz_block'
            else: blk = 'minecraft:smooth_quartz'
            b.set(x, y, z, blk); blocked.add((x, z))
    # Terrace, round walls with glass windows between eight pillars, cyan band, glass dome with quartz ribs.
    for z in range(c - 15, c + 16):
        for x in range(c - 15, c + 16):
            d, a = math.hypot(x - c, z - c), math.degrees(math.atan2(x - c, c - z)) % 360
            rib = min(a % 45, 45 - a % 45) * math.pi / 180 * d < 0.9
            if 13.5 < d <= 14.6: b.set(x, y + 1, z, 'minecraft:smooth_quartz_slab[type=bottom,waterlogged=false]')
            if 11 < d <= 12.4:
                for dy in range(1, 7):
                    window = 2 <= dy <= 4 and not rib
                    b.set(x, y + dy, z, 'minecraft:cyan_stained_glass' if window else 'minecraft:quartz_pillar[axis=y]' if rib else 'minecraft:quartz_bricks')
                b.set(x, y + 6, z, 'minecraft:cyan_concrete')
            if 11 < d <= 13.2: b.set(x, y + 7, z, 'minecraft:smooth_quartz')
            if 12.4 < d <= 13.2: b.set(x, y + 6, z, 'minecraft:gold_block')
            for dy in range(0, 12):   # dome: ellipsoid shell, radius 12.4, height 11
                inner = 12.4 * math.sqrt(max(0.0, 1 - (dy / 11) ** 2))
                if inner - 1.3 < d <= inner:
                    b.set(x, y + 8 + dy, z, 'minecraft:quartz_block' if rib or dy in (4, 8) and d > inner - 0.8 else 'minecraft:light_blue_stained_glass' if dy >= 9 else 'minecraft:cyan_stained_glass')
            if d <= 11:   # floor: Poké Ball emblem with a sea-lantern ring
                b.set(x, y, z, 'minecraft:sea_lantern' if 9 < d <= 10 and int(a) % 30 < 8 else 'minecraft:smooth_quartz')
    pokeball(b, c, y, c, 6)
    b.set(c, y + 19, c, 'minecraft:sea_lantern'); b.set(c, y + 20, c, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    for dx, dz in ((0, 1), (0, -1), (1, 0), (-1, 0)):   # four doorways, 4 wide
        for k in range(-2, 2):
            for d in range(10, 16):
                x, z = c + dx * d + (k if dz else 0), c + dz * d + (k if dx else 0)
                for dy in range(1, 5): b.set(x, y + dy, z, 'minecraft:air')
                if d <= 12: b.set(x, y + 5, z, 'minecraft:cyan_concrete')
    for x in (c - 5, c + 4):   # PCs and the healing counter on the north side, facing the entrance
        b.set(x, y + 1, c - 8, 'cobblemon:pc[facing=south,on=false,part=bottom]'); b.set(x, y + 2, c - 8, 'cobblemon:pc[facing=south,on=false,part=top]')
    for x in range(c - 2, c + 2): b.set(x, y + 1, c - 7, 'minecraft:polished_diorite')
    b.set(c - 1, y + 2, c - 7, 'cobblemon:healing_machine'); b.set(c + 1, y + 2, c - 7, 'minecraft:cake[bites=0]')
    for dx, dz in ((-6, -6), (6, -6), (-6, 6), (6, 6)): b.set(c + dx, y + 10, c + dz, 'minecraft:lantern[hanging=true]'); b.set(c + dx, y + 11, c + dz, 'minecraft:chain[axis=y]')
    for a in range(45, 360, 90):   # plaza corners: quartz posts with lightning rods (urban spawns), benches
        x, z = map(round, sv_xy(a, 19))
        for dy in (1, 2): b.set(x, y + dy, z, 'minecraft:quartz_pillar[axis=y]')
        b.set(x, y + 3, z, 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    for a in range(0, 360, 30):
        if a % 90:
            x, z = map(round, sv_xy(a, 18.5)); lamp_post(b, x, y + 1, z, 3)

# ---- caves inside the mountain (3D biome boxes)
def carve_caves(b, m, surf):
    boxes = {}
    for name, (angle, dist) in CAVES.items():
        cx, cz = map(round, sv_xy(angle, dist)); rx, ry, rz = 9, 4.5, 8; cy = SURFACE + 5
        for z in range(cz - rz, cz + rz + 1):
            for x in range(cx - rx, cx + rx + 1):
                for y in range(SURFACE + 1, cy + 5):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1 and y < surf[(x, z)] - 2:
                        b.set(x, y, z, 'minecraft:air')
        # Tunnel towards the plaza until the slope is low enough to walk in.
        ux, uz = (SV_C - cx) / math.hypot(SV_C - cx, SV_C - cz), (SV_C - cz) / math.hypot(SV_C - cx, SV_C - cz)
        for step in range(0, 40):
            px, pz = cx + ux * step, cz + uz * step
            for w in (-1, 0, 1):
                x, z = round(px - uz * w), round(pz + ux * w)
                for dy in (1, 2, 3): b.set(x, SURFACE + dy, z, 'minecraft:air')
                b.set(x, SURFACE, z, 'minecraft:gravel' if name == 'dripstone_caves' else 'minecraft:moss_block')
            if surf[(round(px), round(pz))] <= SURFACE + 1 and step > rx: break
        rng = b.rng
        for z in range(cz - rz, cz + rz + 1):
            for x in range(cx - rx, cx + rx + 1):
                for y in range(SURFACE, cy + 6):
                    if b.get(x, y, z) == 'minecraft:air' or b.get(x, y + 1, z) != 'minecraft:air' and b.get(x, y - 1, z) != 'minecraft:air': continue
                    floor = b.get(x, y + 1, z) == 'minecraft:air' and b.get(x, y, z) != 'minecraft:air'
                    if name == 'lush_caves':
                        if floor:
                            b.set(x, y, z, 'minecraft:clay' if rng.random() < 0.12 else 'minecraft:moss_block')
                            roll = rng.random()
                            if roll < 0.25: b.set(x, y + 1, z, 'minecraft:moss_carpet')
                            elif roll < 0.3: b.set(x, y + 1, z, rng.choice(['minecraft:azalea', 'minecraft:flowering_azalea']))
                        elif b.get(x, y - 1, z) == 'minecraft:air' and rng.random() < 0.18:   # ceiling: glow berries
                            n = rng.randint(1, 3)
                            for k in range(1, n): b.set(x, y - k, z, 'minecraft:cave_vines_plant[berries=true]')
                            b.set(x, y - n, z, 'minecraft:cave_vines[age=25,berries=true]')
                    else:
                        if floor:
                            b.set(x, y, z, 'minecraft:dripstone_block' if rng.random() < 0.5 else 'minecraft:stone')
                            if rng.random() < 0.08: b.set(x, y + 1, z, 'minecraft:pointed_dripstone[thickness=tip,vertical_direction=up,waterlogged=false]')
                        elif b.get(x, y - 1, z) == 'minecraft:air' and rng.random() < 0.15:
                            b.set(x, y, z, 'minecraft:dripstone_block')
                            b.set(x, y - 1, z, 'minecraft:pointed_dripstone[thickness=tip,vertical_direction=down,waterlogged=false]')
        if name == 'lush_caves':
            b.box(cx - 1, SURFACE, cz - 1, cx + 2, SURFACE, cz + 1, 'minecraft:water[level=0]')
            b.box(cx - 1, SURFACE - 1, cz - 1, cx + 2, SURFACE - 1, cz + 1, 'minecraft:clay')
            b.set(cx, cy + 4, cz, 'minecraft:spore_blossom') if b.get(cx, cy + 5, cz) != 'minecraft:air' else None
        else:   # brick ruin and exposed ores (iron, copper, diamond)
            for dx, dz in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
                for dy in range(1, rng.randint(2, 4)): b.set(cx + dx, SURFACE + dy, cz + dz, 'minecraft:bricks')
            for dx, dz, ore in ((-6, 0, 'iron_ore'), (6, 1, 'copper_ore'), (0, -6, 'diamond_ore'), (2, 6, 'coal_ore')):
                b.set(cx + dx, SURFACE + 1, cz + dz, 'minecraft:' + ore)
        boxes[name] = {'from': [cx - rx - 1, SURFACE - 1, cz - rz - 1], 'to': [cx + rx + 1, SURFACE + 11, cz + rz + 1]}
    return boxes

# ---- arrival, paths, lamps
def arrival_pier(b, surf, blocked):
    c, z0 = SV_C, SV_C + 72
    for z in range(z0 - 6, z0 + 6):
        for x in range(c - 6, c + 7):
            for y in range(SURFACE - 4, SURFACE): b.set(x, y, z, 'minecraft:stone')
            clear_above(b, x, SURFACE + 1, z, 14)
            b.set(x, SURFACE, z, 'minecraft:cyan_wool' if x in (c - 6, c + 6) else 'minecraft:smooth_quartz'); blocked.add((x, z)); surf[(x, z)] = SURFACE
    pokeball(b, c, SURFACE, z0, 4, colours=('minecraft:cyan_wool', 'minecraft:white_wool'))
    for x in (c - 6, c + 6):
        for z in (z0 - 6, z0 + 5): lamp_post(b, x, SURFACE + 1, z, 3)
    for z in range(z0 + 6, z0 + 19):   # wooden pier into the sea
        for x in range(c - 1, c + 2):
            b.set(x, SURFACE + 1, z, 'minecraft:spruce_planks'); clear_above(b, x, SURFACE + 2, z, 6); blocked.add((x, z))
        if z % 4 == 0:
            for x in (c - 2, c + 2):
                for y in range(surf.get((x, z), SURFACE - 6), SURFACE + 2): b.set(x, y, z, 'minecraft:spruce_log[axis=y]')
                b.set(x, SURFACE + 2, z, 'minecraft:spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]')
                b.set(x, SURFACE + 3, z, 'minecraft:lantern[hanging=false]')
    for z in range(SV_C + SV_PLAZA, z0 - 6):   # straight avenue from the plaza
        for x in range(c - 2, c + 3):
            if (x, z) not in surf: continue
            y = min(surf[(x, z)], SURFACE + 2); surf[(x, z)] = y
            for yy in range(SURFACE - 3, y): b.set(x, yy, z, 'minecraft:dirt')
            b.set(x, y, z, 'minecraft:smooth_quartz' if abs(x - c) <= 1 else 'minecraft:polished_andesite'); clear_above(b, x, y + 1, z, 10); blocked.add((x, z))

def path_cells(b, surf, blocked, pts, width=1):
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        steps = int(max(abs(x1 - x0), abs(z1 - z0))) + 1
        for i in range(steps):
            t = i / max(1, steps - 1); px, pz = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            for dz in range(-width - 2, width + 3):
                for dx in range(-width - 2, width + 3):
                    x, z = round(px + dx), round(pz + dz)
                    if (x, z) not in surf: continue
                    blocked.add((x, z))
                    if dx * dx + dz * dz > width * width + 1 or b.get(x, SURFACE, z) == 'minecraft:barrier': continue
                    y = surf[(x, z)]
                    if y < SURFACE:   # bridge over water at sea level
                        b.set(x, SURFACE, z, 'minecraft:spruce_planks'); clear_above(b, x, SURFACE + 1, z, 3)
                    elif b.get(x, y, z) not in ('minecraft:smooth_quartz', 'minecraft:polished_andesite', 'minecraft:spruce_planks'):
                        b.set(x, y, z, 'minecraft:dirt_path'); clear_above(b, x, y + 1, z, 3)

def winding_path(b, surf, blocked, angle, reach):
    pts = [sv_xy(angle + 9 * math.sin(d / 9 + angle), d) for d in range(SV_PLAZA, reach + 1, 3)]
    path_cells(b, surf, blocked, pts)
    b.path_points = getattr(b, 'path_points', []) + pts

def lamps(b, surf, blocked, biome_of):
    for i, (px, pz) in enumerate(b.path_points):
        if i % 4 != 2: continue
        x, z = round(px) + 2, round(pz)
        if (x, z) not in surf or surf[(x, z)] < SURFACE or biome_of(x, z) in SNOWY: continue
        if any(biome_of(x + dx, z + dz) in SNOWY for dx in (-8, 0, 8) for dz in (-8, 0, 8) if (x + dx, z + dz) in surf): continue
        y = surf[(x, z)] + 1
        if b.get(x, y, z) == 'minecraft:air' and b.get(x, y - 1, z) != 'minecraft:dirt_path': lamp_post(b, x, y, z, 3)

# ---- statues (wool and terracotta: concrete would block wild spawns nearby)
def ellipsoid(b, cx, cy, cz, rx, ry, rz, block, cond=None):
    for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
        for z in range(math.floor(cz - rz), math.ceil(cz + rz) + 1):
            for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1 and (cond is None or cond(x, y, z)):
                    b.set(x, y, z, block)

def paint_front(b, x, y, z, block, depth=8):
    """Paint the first solid block seen from the south (+z) at column (x, y)."""
    for zz in range(z, z - depth, -1):
        if b.get(x, y, zz) != 'minecraft:air': b.set(x, y, zz, block); return

def stroke(b, pts, radius, block_at):
    for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)) * 2) + 1
        for i in range(n + 1):
            t = i / n; ellipsoid(b, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t, *radius, block_at(t))

def footprint(blocked, x, z, r):
    blocked.update((x + dx, z + dz) for dz in range(-r, r + 1) for dx in range(-r, r + 1))

def pikachu(b, gx, gy, gz, blocked):
    Y, K, R, Br = 'minecraft:yellow_wool', 'minecraft:black_wool', 'minecraft:red_wool', 'minecraft:brown_wool'
    for s in (-1, 1): ellipsoid(b, gx + 2.5 * s, gy + 0.6, gz + 1.5, 1.7, 1.1, 2.4, Y)
    ellipsoid(b, gx, gy + 5, gz, 4.6, 5, 4, Y)
    ellipsoid(b, gx, gy + 7, gz, 4.6, 5, 4, Br, cond=lambda x, y, z: z <= gz - 3 and y in (gy + 5, gy + 8))
    for s in (-1, 1): ellipsoid(b, gx + 3.6 * s, gy + 6.5, gz + 2.6, 1.3, 1.3, 1.7, Y)
    ellipsoid(b, gx, gy + 12, gz + 0.5, 5.2, 4.3, 4.3, Y)
    for s in (-1, 1): stroke(b, [(gx + 3 * s, gy + 15, gz), (gx + 6.5 * s, gy + 21.5, gz - 0.5)], (1.3, 1.3, 1.0), lambda t: K if t > 0.65 else Y)
    stroke(b, [(gx, gy + 3, gz - 4), (gx, gy + 5, gz - 6.5)], (1.0, 1.2, 1.2), lambda t: Br)
    stroke(b, [(gx, gy + 5, gz - 6.5), (gx, gy + 8, gz - 5.5), (gx, gy + 10, gz - 8.5), (gx, gy + 13, gz - 7.5), (gx, gy + 16, gz - 11)], (1.0, 1.6, 1.6), lambda t: Y)
    for s in (-1, 1):
        for y in (gy + 12, gy + 13): paint_front(b, gx + 2 * s, y, gz + 7, K)
        paint_front(b, gx + 2 * s, gy + 14, gz + 7, K)
        for x in (gx + 3 * s, gx + 4 * s):
            for y in (gy + 10, gy + 11): paint_front(b, x, y, gz + 7, R)
    paint_front(b, gx, gy + 11, gz + 7, K)
    footprint(blocked, gx, gz, 12)

def snorlax(b, gx, gy, gz, blocked):
    T, C, K = 'minecraft:cyan_terracotta', 'minecraft:white_terracotta', 'minecraft:black_wool'
    ellipsoid(b, gx, gy + 7, gz, 8, 7.5, 7, T)
    ellipsoid(b, gx, gy + 6.5, gz + 2.2, 6.4, 6, 5.4, C)
    for s in (-1, 1):
        ellipsoid(b, gx + 4.5 * s, gy + 1.6, gz + 6, 2.6, 2, 1.8, C)
        ellipsoid(b, gx + 8.2 * s, gy + 8, gz + 1, 2.2, 4, 2.2, T)
        ellipsoid(b, gx + 4 * s, gy + 20, gz, 1.4, 1.7, 1.3, T)
    ellipsoid(b, gx, gy + 16, gz + 0.5, 5.6, 4.6, 5, T)
    ellipsoid(b, gx, gy + 15, gz + 2.4, 4.6, 3.4, 3.4, C, cond=lambda x, y, z: y <= gy + 16)
    for x in (gx - 3, gx - 2, gx + 2, gx + 3): paint_front(b, x, gy + 16, gz + 8, K)
    for x in range(gx - 1, gx + 2): paint_front(b, x, gy + 14, gz + 8, K)
    for s in (-1, 1): paint_front(b, gx + 4 * s, gy + 1, gz + 9, 'minecraft:brown_terracotta')
    footprint(blocked, gx, gz, 13)

def pokeball_statue(b, cx, cz, blocked):
    ellipsoid(b, cx, SURFACE - 4, cz, 9, 6, 9, 'minecraft:stone')
    ellipsoid(b, cx, SURFACE - 1, cz, 8, 2.5, 8, 'minecraft:moss_block', cond=lambda x, y, z: b.get(x, y, z) in ('minecraft:water[level=0]', 'minecraft:stone', 'minecraft:air'))
    cy = SURFACE + 7
    ellipsoid(b, cx, cy, cz, 6.5, 6.5, 6.5, 'minecraft:cyan_wool', cond=lambda x, y, z: y > cy)
    ellipsoid(b, cx, cy, cz, 6.5, 6.5, 6.5, 'minecraft:white_wool', cond=lambda x, y, z: y < cy)
    ellipsoid(b, cx, cy, cz, 6.5, 6.5, 6.5, 'minecraft:black_wool', cond=lambda x, y, z: y == cy)
    # Button facing the island centre (north-west).
    for dy in range(-2, 3):
        for dk in range(-2, 3):
            d = math.hypot(dy, dk)
            if d > 2.4: continue
            x, z = round(cx - 4.4 + dk * 0.7), round(cz - 4.4 - dk * 0.7)
            b.set(x, cy + dy, z, 'minecraft:white_wool' if d <= 1.2 else 'minecraft:black_wool')
    footprint(blocked, cx, cz, 9)

# ---- landmarks the spawn rules look for, then scattered vegetation
def spot(b, surf, blocked, cells, size, rng):
    """A dry, fairly flat, unblocked square of side 2*size+1 inside the biome, as central as possible."""
    if not cells: return None
    mx, mz = sum(x for x, _ in cells) / len(cells), sum(z for _, z in cells) / len(cells)
    own = set(cells)
    for x, z in sorted(cells, key=lambda p: (p[0] - mx) ** 2 + (p[1] - mz) ** 2):
        area = [(x + dx, z + dz) for dz in range(-size, size + 1) for dx in range(-size, size + 1)]
        if all(p in own and p not in blocked and surf[p] >= SURFACE for p in area):
            ys = [surf[p] for p in area]
            if max(ys) - min(ys) <= 2: return x, z, max(ys)
    return None

def level(b, surf, blocked, x, z, size, y, top=None):
    for dz in range(-size, size + 1):
        for dx in range(-size, size + 1):
            p = (x + dx, z + dz)
            for yy in range(surf[p], y): b.set(p[0], yy, p[1], 'minecraft:dirt')
            if top: b.set(p[0], y, p[1], top)
            elif surf[p] != y: b.set(p[0], y, p[1], b.get(p[0], surf[p], p[1]))
            clear_above(b, p[0], y + 1, p[1], 10); surf[p] = y; blocked.add(p)

def landmarks(b, m, surf, blocked, by_biome):
    rng = b.rng
    def at(biome, size):
        s = spot(b, surf, blocked, by_biome[biome], size, rng)
        if s: level(b, surf, blocked, s[0], s[1], size, s[2])
        return s
    s = at('desert', 3)
    if s:   # roofed sandstone shrine (covered sand floor) beside a small ruin
        x, z, y = s
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                b.set(x + dx, y, z + dz, 'minecraft:sand'); b.set(x + dx, y + 4, z + dz, 'minecraft:cut_sandstone')
                if max(abs(dx), abs(dz)) == 3 and not (dz == 3 and abs(dx) <= 1):
                    for dy in (1, 2, 3): b.set(x + dx, y + dy, z + dz, 'minecraft:chiseled_sandstone' if dy == 2 else 'minecraft:sandstone')
        b.set(x, y + 1, z - 1, 'minecraft:orange_terracotta'); b.set(x, y + 5, z, 'minecraft:chiseled_sandstone')
    s = at('jungle', 2)
    if s:
        x, z, y = s
        for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            for dy in range(1, rng.randint(2, 5)): b.set(x + dx, y + dy, z + dz, rng.choice(['minecraft:mossy_cobblestone', 'minecraft:chiseled_stone_bricks']))
        b.set(x, y, z, 'minecraft:cobblestone'); b.set(x + 1, y, z, 'minecraft:mossy_cobblestone')
    s = at('meadow', 2)
    if s:   # Cobblemon saccharine tree and a picnic cake
        x, z, y = s
        for dy in range(1, 6): b.set(x, y + dy, z, 'cobblemon:saccharine_log[axis=y]')
        ellipsoid(b, x, y + 6, z, 2.6, 1.8, 2.6, 'cobblemon:saccharine_leaves[age=0,distance=1,persistent=true,waterlogged=false]',
                  cond=lambda xx, yy, zz: b.get(xx, yy, zz) == 'minecraft:air')
        b.set(x + 2, y + 1, z + 2, 'minecraft:oak_planks'); b.set(x + 2, y + 2, z + 2, 'minecraft:cake[bites=0]')
    s = at('birch_forest', 2)
    if s:
        x, z, y = s
        for dx, berry in ((-2, 'oran'), (0, 'pecha'), (2, 'cheri')): b.set(x + dx, y + 1, z, f'cobblemon:{berry}_berry[age=3,rooted=false]')
    s = at('dark_forest', 3)
    if s:   # fishing pond
        x, z, y = s
        for dz in range(-2, 3):
            for dx in range(-2, 3):
                b.set(x + dx, y - 2, z + dz, 'minecraft:clay')
                for yy in (y - 1, y): b.set(x + dx, yy, z + dz, 'minecraft:water[level=0]')
    for biome in ('plains', 'taiga'):
        for _ in range(2):
            s = at(biome, 1)
            if s:
                x, z, y = s
                b.set(x, y + 1, z, 'minecraft:pumpkin'); b.set(x + 1, y + 1, z, 'minecraft:pumpkin')
    s = at('plains', 1)
    if s: b.set(s[0], s[2] + 1, s[1], 'minecraft:cobblestone'); b.set(s[0], s[2] + 2, s[1], 'minecraft:lightning_rod[facing=up,powered=false,waterlogged=false]')
    for x, z in by_biome['stony_peaks'][::97]:
        if (x, z) not in blocked: b.set(x, surf[(x, z)], z, 'minecraft:iron_ore')
    cells = [p for p in by_biome['ice_spikes'] if p not in blocked]
    for x, z in rng.sample(cells, min(9, len(cells))):
        h, y = rng.randint(5, 14), surf[(x, z)] + 1
        for dy in range(h): b.set(x, y + dy, z, 'minecraft:packed_ice')
        if h > 8:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for dy in range(h // 2): b.set(x + dx, y + dy, z + dz, 'minecraft:packed_ice')
        blocked.add((x, z))

def round_tree(b, x, y, z, kind, h, r, flat=0.8, log=None):
    log = log or f'minecraft:{kind}_log[axis=y]'
    leaves = f'minecraft:{kind}_leaves' + LEAF
    for dy in range(h): b.set(x, y + dy, z, log)
    rng = b.rng
    for dy in range(-math.ceil(r * flat), math.ceil(r * flat) + 1):
        for dz in range(-r - 1, r + 2):
            for dx in range(-r - 1, r + 2):
                if (dx * dx + dz * dz) / (r * r) + (dy / (r * flat)) ** 2 <= 1 + 0.25 * rng.random() and rng.random() > 0.06:
                    if b.get(x + dx, y + h + dy, z + dz) == 'minecraft:air': b.set(x + dx, y + h + dy, z + dz, leaves)

def big_tree2(b, x, y, z, kind, h, r):
    """2x2 trunk (dark oak, jungle) with a wide crown."""
    for dx in (0, 1):
        for dz in (0, 1):
            for dy in range(h): b.set(x + dx, y + dy, z + dz, f'minecraft:{kind}_log[axis=y]')
    round_tree(b, x, y + h - 1, z, kind, 1, r, 0.55)
    if kind == 'jungle':
        for dx, dz in ((3, 0), (-3, 1)): round_tree(b, x + dx, y + h - 5, z + dz, kind, 0, 2, 0.6)

def acacia(b, x, y, z):
    dx, dz = b.rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
    for dy in range(3): b.set(x, y + dy, z, 'minecraft:acacia_log[axis=y]')
    for k in (1, 2): b.set(x + dx * k, y + 2 + k, z + dz * k, 'minecraft:acacia_log[axis=y]')
    tx, tz, ty = x + 2 * dx, z + 2 * dz, y + 5
    for ddz in range(-3, 4):
        for ddx in range(-3, 4):
            if abs(ddx) + abs(ddz) <= 4 and b.get(tx + ddx, ty, tz + ddz) == 'minecraft:air': b.set(tx + ddx, ty, tz + ddz, 'minecraft:acacia_leaves' + LEAF)
            if abs(ddx) + abs(ddz) <= 2 and b.get(tx + ddx, ty + 1, tz + ddz) == 'minecraft:air': b.set(tx + ddx, ty + 1, tz + ddz, 'minecraft:acacia_leaves' + LEAF)

def palm(b, x, y, z):
    dx, dz = b.rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
    for dy in range(6): b.set(x + (dx if dy > 3 else 0), y + dy, z + (dz if dy > 3 else 0), 'minecraft:jungle_log[axis=y]')
    tx, ty, tz = x + dx, y + 6, z + dz
    b.set(tx, ty, tz, 'minecraft:jungle_leaves' + LEAF)
    for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for k in (1, 2, 3): b.set(tx + ddx * k, ty - (k == 3), tz + ddz * k, 'minecraft:jungle_leaves' + LEAF)

def decorate(b, surf, blocked, by_biome):
    rng = b.rng
    FLOWERS_FF = ['poppy', 'red_tulip', 'orange_tulip', 'dandelion', 'white_tulip', 'lily_of_the_valley', 'pink_tulip', 'cornflower', 'allium', 'oxeye_daisy']
    def free(x, z, r=0):
        return all((x + dx, z + dz) not in blocked for dz in range(-r, r + 1) for dx in range(-r, r + 1))
    def place(biome, chance, fn, room=0, dry=True):
        for x, z in by_biome[biome]:
            y = surf[(x, z)]
            if rng.random() >= chance or not free(x, z, room) or (dry and y < SURFACE): continue
            if b.get(x, y + 1, z) != 'minecraft:air': continue
            fn(x, y + 1, z)
            if room: blocked.update((x + dx, z + dz) for dz in (-1, 0, 1) for dx in (-1, 0, 1))
    grounded = lambda fn: lambda x, y, z: fn(x, y, z) if on_ground(b, x, y, z) else None
    on = lambda block, *under: lambda x, y, z: b.set(x, y, z, block) if b.get(x, y - 1, z).split('[')[0] in under else None
    flowers = ['dandelion', 'poppy', 'cornflower', 'oxeye_daisy', 'azure_bluet']
    place('plains', 0.004, grounded(lambda x, y, z: round_tree(b, x, y, z, 'oak', 5, 3)), 3)
    place('plains', 0.45, lambda x, y, z: plants(b, x, y, z, flowers))
    place('forest', 0.03, grounded(lambda x, y, z: round_tree(b, x, y, z, 'oak', rng.randint(5, 7), 3)), 3)
    place('forest', 0.008, grounded(lambda x, y, z: round_tree(b, x, y, z, 'birch', 6, 2)), 2)
    place('forest', 0.3, lambda x, y, z: plants(b, x, y, z, flowers))
    place('flower_forest', 0.008, grounded(lambda x, y, z: round_tree(b, x, y, z, 'oak', 5, 3)), 3)
    place('flower_forest', 0.6, grounded(lambda x, y, z: b.set(x, y, z, 'minecraft:' + rng.choice(FLOWERS_FF))))
    place('birch_forest', 0.035, grounded(lambda x, y, z: round_tree(b, x, y, z, 'birch', rng.randint(6, 8), 2, 1.1)), 2)
    place('birch_forest', 0.3, lambda x, y, z: plants(b, x, y, z, flowers))
    place('dark_forest', 0.022, grounded(lambda x, y, z: big_tree2(b, x, y, z, 'dark_oak', rng.randint(6, 8), 4)), 3)
    place('dark_forest', 0.004, grounded(lambda x, y, z: huge_mushroom(b, x, y, z, rng.random() < 0.5)), 3)
    place('dark_forest', 0.15, lambda x, y, z: plants(b, x, y, z, ['lily_of_the_valley']))
    place('swamp', 0.012, grounded(lambda x, y, z: round_tree(b, x, y, z, 'oak', 5, 3, 0.6)), 3)
    place('swamp', 0.25, lambda x, y, z: plants(b, x, y, z, ['blue_orchid']))
    for x, z in by_biome['swamp']:
        if surf[(x, z)] < SURFACE and b.get(x, SURFACE, z).startswith('minecraft:water') and rng.random() < 0.15: b.set(x, SURFACE + 1, z, 'minecraft:lily_pad')
    for biome in ('taiga', 'snowy_taiga', 'snowy_plains'):
        chance = {'taiga': 0.035, 'snowy_taiga': 0.035, 'snowy_plains': 0.003}[biome]
        place(biome, chance, grounded(lambda x, y, z: tree(b, x, y, z, 'spruce', rng.randint(7, 10))), 3)
    place('taiga', 0.2, on('minecraft:fern', 'minecraft:grass_block', 'minecraft:podzol'))
    place('taiga', 0.015, on('minecraft:sweet_berry_bush[age=3]', 'minecraft:grass_block', 'minecraft:podzol'))
    place('cherry_grove', 0.012, grounded(lambda x, y, z: round_tree(b, x, y, z, 'cherry', rng.randint(5, 6), 4, 0.6)), 4)
    place('cherry_grove', 0.4, on('minecraft:pink_petals[facing=north,flower_amount=4]', 'minecraft:grass_block'))
    place('meadow', 0.55, grounded(lambda x, y, z: b.set(x, y, z, 'minecraft:' + rng.choice(['allium', 'azure_bluet', 'cornflower', 'oxeye_daisy', 'dandelion', 'short_grass', 'short_grass']))))
    place('jungle', 0.014, grounded(lambda x, y, z: big_tree2(b, x, y, z, 'jungle', rng.randint(11, 15), 4)), 4)
    place('jungle', 0.03, grounded(lambda x, y, z: round_tree(b, x, y, z, 'jungle', 1, 2, 0.7, 'minecraft:oak_log[axis=y]')), 1)
    place('jungle', 0.01, on('minecraft:melon', 'minecraft:grass_block', 'minecraft:podzol'))
    place('jungle', 0.008, grounded(lambda x, y, z: [b.set(x, y + dy, z, 'minecraft:bamboo[age=0,leaves=large,stage=0]') for dy in range(rng.randint(5, 10))]))
    place('jungle', 0.4, lambda x, y, z: plants(b, x, y, z, ['poppy', 'dandelion']))
    place('savanna', 0.01, grounded(lambda x, y, z: acacia(b, x, y, z)), 3)
    place('savanna', 0.5, lambda x, y, z: plants(b, x, y, z, ['dandelion', 'poppy']))
    place('desert', 0.006, on('minecraft:cactus[age=0]', 'minecraft:sand'), 1)
    place('desert', 0.02, on('minecraft:dead_bush', 'minecraft:sand'))
    place('badlands', 0.02, on('minecraft:dead_bush', 'minecraft:red_sand'))
    place('badlands', 0.003, on('minecraft:cactus[age=0]', 'minecraft:red_sand'), 1)
    place('beach', 0.01, lambda x, y, z: palm(b, x, y, z) if b.get(x, y - 1, z) == 'minecraft:sand' else None, 2)
    place('stony_peaks', 0.01, lambda x, y, z: b.set(x, y, z, rng.choice(['minecraft:cobblestone', 'minecraft:mossy_cobblestone'])))
    for x in [p for p in by_biome['desert'] + by_biome['badlands'] if b.get(p[0], surf[p] + 1, p[1]) == 'minecraft:cactus[age=0]']:
        b.set(x[0], surf[x] + 2, x[1], 'minecraft:cactus[age=0]')
    # Underwater: kelp and seagrass, corals in the warm sea, sugar cane on the river banks.
    for biome in ('ocean', 'warm_ocean', 'river'):
        for x, z in by_biome[biome]:
            y = surf[(x, z)]
            if y >= SURFACE - 1 or b.get(x, y + 1, z) != 'minecraft:water[level=0]': continue
            roll = rng.random()
            if biome == 'warm_ocean' and roll < 0.18: b.set(x, y + 1, z, 'minecraft:' + rng.choice(['tube', 'brain', 'bubble', 'fire', 'horn']) + '_coral_block')
            elif biome != 'river' and roll < 0.26 and y <= SURFACE - 4:
                for yy in range(y + 1, SURFACE - 1): b.set(x, yy, z, 'minecraft:kelp_plant')
                b.set(x, SURFACE - 1, z, 'minecraft:kelp[age=20]')
            elif roll < 0.5: b.set(x, y + 1, z, 'minecraft:seagrass')
    for x, z in by_biome['river']:
        for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            p = (x + dx, z + dz)
            if p in surf and surf[p] == SURFACE and p not in blocked and rng.random() < 0.05 and b.get(p[0], SURFACE + 1, p[1]) == 'minecraft:air' \
                    and b.get(p[0], SURFACE, p[1]).startswith(('minecraft:grass_block', 'minecraft:sand')):
                for dy in (1, 2): b.set(p[0], SURFACE + dy, p[1], 'minecraft:sugar_cane[age=0]')
    # Snow cover on the cold side and the mountain tops.
    for biome in SNOWY:
        for x, z in by_biome[biome]:
            y = surf[(x, z)]
            if b.get(x, y, z) in ('minecraft:grass_block[snowy=true]', 'minecraft:snow_block') and b.get(x, y + 1, z) == 'minecraft:air' and (x, z) not in blocked:
                b.set(x, y + 1, z, 'minecraft:snow[layers=1]')

# ---- biome boxes for /fillbiome and per-biome inventories for the spawn analysis
def biome_boxes(quart, caves, limit=32768):
    """Merge equal 4x4 biome cells into rectangles below the /fillbiome volume limit; caves last (3D)."""
    n, rows = SV // 4, []
    keep = lambda qx, qz: math.hypot(qx * 4 + 1.5 - SV_C, qz * 4 + 1.5 - SV_C) <= SV_SEA + 3
    runs = {}
    for qz in range(n):
        qx = 0
        while qx < n:
            if not keep(qx, qz): qx += 1; continue
            biome, start = quart[(qx, qz)], qx
            while qx < n and keep(qx, qz) and quart[(qx, qz)] == biome: qx += 1
            runs.setdefault((start, qx - 1, biome), []).append(qz)
    max_area = limit // (HEIGHT * 16)   # in 4x4 cells
    boxes = []
    for (x0, x1, biome), zs in sorted(runs.items(), key=lambda kv: (kv[1][0], kv[0][0])):
        groups, cur = [], [zs[0]]
        for qz in zs[1:]:
            if qz == cur[-1] + 1: cur.append(qz)
            else: groups.append(cur); cur = [qz]
        groups.append(cur)
        width = x1 - x0 + 1
        for g in groups:
            depth = max(1, max_area // min(width, max_area))
            for xs in range(x0, x1 + 1, max_area):
                xe = min(x1, xs + max_area - 1)
                for k in range(0, len(g), depth):
                    zs0, zs1 = g[k], g[min(len(g), k + depth) - 1]
                    boxes.append({'biome': 'minecraft:' + biome, 'from': [xs * 4, 0, zs0 * 4], 'to': [xe * 4 + 3, HEIGHT - 1, zs1 * 4 + 3]})
    for name, box in sorted(caves.items()): boxes.append({'biome': 'minecraft:' + name, **box})
    return boxes

def in_box(box, x, y, z):
    return all(box['from'][i] <= v <= box['to'][i] for i, v in enumerate((x, y, z)))

def region_inventory(b, biome, columns, caves):
    """What a biome region offers to spawn rules: blocks present, fluids and open/covered ground spots."""
    if columns is None:   # cave: the 3D box only
        box = caves[biome]; (x0, y0, z0), (x1, y1, z1) = box['from'], box['to']
        columns, yr = [(x, z) for z in range(z0, z1 + 1) for x in range(x0, x1 + 1)], range(y0, y1 + 1)
        cell = lambda x, y, z: b.get(x, y, z)
    else:
        yr = range(HEIGHT)
        cell = lambda x, y, z: 'minecraft:stone' if any(in_box(bx, x, y, z) for bx in caves.values()) else b.get(x, y, z)
    blocks, water, lava, open_sky, covered = set(), False, False, False, False
    for x, z in columns:
        column = [cell(x, y, z) for y in yr]
        for blk in column:
            if blk not in ('minecraft:air', 'minecraft:barrier'): blocks.add(blk.split('[')[0])
        water |= any(c.startswith('minecraft:water') for c in column)
        lava |= any(c.startswith('minecraft:lava') for c in column)
        for i in range(len(column) - 2):
            solid = column[i] not in ('minecraft:air', 'minecraft:barrier') and not column[i].startswith('minecraft:lava')
            surface_water = column[i].startswith('minecraft:water') and not column[i + 1].startswith('minecraft:water')
            if (solid and not column[i].startswith('minecraft:water') and column[i + 1] == 'minecraft:air' and column[i + 2] == 'minecraft:air') or surface_water:
                above = any(c != 'minecraft:air' for c in column[i + 1:]) if biome not in CAVES else True
                covered |= above; open_sky |= not above
    return {'biome': 'minecraft:' + biome, 'blocks': sorted(blocks), 'water': water, 'lava': lava, 'open_sky': open_sky, 'covered': covered}

# ---------------------------------------------------------------- preview
COLORS = [('yellow_wool', (240, 200, 40)), ('black_wool', (25, 25, 30)), ('red_wool', (190, 40, 40)), ('brown_wool', (110, 70, 40)),
          ('white_wool', (235, 235, 235)), ('cyan_wool', (22, 150, 160)), ('white_terracotta', (210, 180, 160)), ('cyan_terracotta', (70, 90, 98)),
          ('light_blue_stained_glass', (120, 190, 230)), ('pink_petals', (240, 170, 200)), ('dark_oak_leaves', (40, 90, 35)),
          ('red_mushroom_block', (180, 40, 40)), ('brown_mushroom_block', (140, 105, 80)), ('melon', (110, 160, 50)), ('sugar_cane', (120, 190, 90)),
          ('planks', (150, 110, 70)), ('clay', (160, 165, 180)), ('acacia_leaves', (110, 140, 40)), ('jungle_leaves', (50, 140, 40)),
          ('end_stone', (222, 222, 160)), ('red_sand', (190, 100, 40)), ('netherrack', (110, 40, 40)), ('crimson', (150, 30, 40)),
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
    for z in range(b.size):
        row = bytearray()
        for x in range(b.size):
            rgb, top = (18, 22, 30), None
            for y in range(HEIGHT - 1, -1, -1):
                blk = b.get(x, y, z)
                if blk not in ('minecraft:air', 'minecraft:barrier'): rgb, top = color(blk), y; break
            if top is not None:
                shade = 0.75 + 0.5 * (top / HEIGHT); rgb = tuple(min(255, int(c * shade)) for c in rgb)
            row += bytes(rgb) * scale
        for _ in range(scale): rows.append(b'\x00' + bytes(row))
    w = h = b.size * scale
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
    path.write_bytes(png)

def oblique_view(b, path, S=5, T=3, F=4):
    """View from the south (arrival side) at roughly 45 degrees: top faces plus darker south faces, painter's order."""
    N, AIR = b.size, ('minecraft:air', 'minecraft:barrier')
    W, H = N * S, N * T + HEIGHT * F + 20
    img = bytearray()
    for py in range(H): t = py / H; img += bytes((int(150 + 70 * t), int(190 + 45 * t), int(230 + 15 * t))) * W
    def put(x0, y0, h, rgb):
        for yy in range(max(0, y0), min(H, y0 + h)): img[(yy * W + x0) * 3:(yy * W + x0 + S) * 3] = bytes(rgb) * S
    for z in range(N):
        for y in range(HEIGHT):
            for x in range(N):
                blk = b.get(x, y, z)
                if blk in AIR: continue
                up, front, water = b.get(x, y + 1, z), b.get(x, y, z + 1), blk.startswith('minecraft:water')
                if water and up.startswith('minecraft:water'): continue
                if not (up in AIR or front in AIR or up.startswith('minecraft:water') or front.startswith('minecraft:water')): continue
                rgb, lift = color(blk), 0.82 + 0.35 * y / HEIGHT
                sy = z * T - y * F + HEIGHT * F
                put(x * S, sy, T, tuple(min(255, int(c * lift)) for c in rgb))
                if not water: put(x * S, sy + T, F, tuple(int(c * lift * 0.68) for c in rgb))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    raw = b''.join(b'\x00' + bytes(img[r * W * 3:(r + 1) * W * 3]) for r in range(H))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

def biome_commands(cells, ox, oy, oz):
    """Absolute /fillbiome commands for the SafariVip biome boxes pasted with its origin at (ox, oy, oz)."""
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
        oblique_view(b, out / f'atlas-warp-{b.name.lower()}-view.png')
        summary[b.name] = {'file': f'atlas-warp-{b.name.lower()}.litematic', 'size': [b.size, HEIGHT, b.size],
                           'arrival': b.arrival, 'palette': len(b.palette), 'blocks': sum(1 for v in b.cells if v), 'notes': b.notes}
        summary[b.name]['water_leaks'] = water_leaks(b)
        if b.name == 'SafariVip':
            (out / 'safarivip-zones.json').write_text(json.dumps(b.zones, indent=1) + '\n')
            (out / 'safarivip-biomes.json').write_text(json.dumps(b.biome_boxes, indent=1) + '\n')
            if args.safarivip_origin:
                (out / 'safarivip-fillbiome.txt').write_text('\n'.join(biome_commands(b.biome_boxes, *args.safarivip_origin)) + '\n')
        print(b.name, summary[b.name]['blocks'], 'blocos,', len(b.palette), 'tipos, vazamentos de água:', summary[b.name]['water_leaks'])
    (out / 'warps.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main()
