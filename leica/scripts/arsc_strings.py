"""Find and replace CJK strings in resources.arsc that the default, en and vi locales display.

  arsc_strings.py list  <resources.arsc> <out.json>                 (string -> [resource names])
  arsc_strings.py apply <resources.arsc> <map.json> <out.arsc>      (rewrites the global string pool)

Only values used by the default, en and vi configs are considered; other locales stay intact.
"""
import json, re, struct, sys

CJK = re.compile('[\\u3040-\\u30ff\\u3400-\\u9fff\\uac00-\\ud7af]')
SHOWN_LANGS = {'', 'en', 'vi'}


def u8len(d, o):
    n = d[o]; o += 1
    if n & 0x80:
        n = ((n & 0x7f) << 8) | d[o]; o += 1
    return n, o


def u16len(d, o):
    n = struct.unpack_from('<H', d, o)[0]; o += 2
    if n & 0x8000:
        n = ((n & 0x7fff) << 16) | struct.unpack_from('<H', d, o)[0]; o += 2
    return n, o


class Pool:
    def __init__(self, d, start):
        (self.type, self.hsize, self.size, self.count, self.styles, self.flags,
         self.sstart, self.ystart) = struct.unpack_from('<HHIIIIII', d, start)
        self.start = start
        self.utf8 = bool(self.flags & 0x100)
        offs = struct.unpack_from(f'<{self.count}I', d, start + self.hsize)
        self.style_offs = d[start + self.hsize + 4 * self.count: start + self.hsize + 4 * (self.count + self.styles)]
        self.style_data = d[start + self.ystart: start + self.size] if self.styles else b''
        self.strings = []
        base = start + self.sstart
        for off in offs:
            o = base + off
            if self.utf8:
                _, o = u8len(d, o)
                n, o = u8len(d, o)
                self.strings.append(d[o:o + n].decode('utf-8', 'surrogatepass'))
            else:
                n, o = u16len(d, o)
                self.strings.append(d[o:o + 2 * n].decode('utf-16-le', 'surrogatepass'))

    def encode(self):
        data, offs = bytearray(), []
        for s in self.strings:
            offs.append(len(data))
            if self.utf8:
                b = s.encode('utf-8', 'surrogatepass')
                for n in (len(s.encode('utf-16-le', 'surrogatepass')) // 2, len(b)):
                    data += bytes([0x80 | (n >> 8), n & 0xff]) if n > 0x7f else bytes([n])
                data += b + b'\0'
            else:
                b = s.encode('utf-16-le', 'surrogatepass')
                n = len(b) // 2
                data += struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff) if n > 0x7fff else struct.pack('<H', n)
                data += b + b'\0\0'
        while len(data) % 4:
            data += b'\0'
        sstart = self.hsize + 4 * (self.count + self.styles)
        ystart = sstart + len(data) if self.styles else 0
        size = sstart + len(data) + len(self.style_data)
        head = struct.pack('<HHIIIIII', self.type, self.hsize, size, self.count, self.styles, self.flags, sstart, ystart)
        head += b'\0' * (self.hsize - len(head))
        return head + struct.pack(f'<{self.count}I', *offs) + self.style_offs + bytes(data) + self.style_data


def walk_values(d, pool_end, total):
    """Yield (string index, resource name) for string values in non-CJK configs."""
    o = pool_end
    while o < total:
        ctype, chs, csize = struct.unpack_from('<HHI', d, o)
        if ctype == 0x0200:
            pkg_end = o + csize
            type_pool = Pool(d, o + struct.unpack_from('<I', d, o + 8 + 4 + 256)[0])
            key_pool = Pool(d, o + struct.unpack_from('<I', d, o + 8 + 4 + 256 + 8)[0])
            p = o + chs
            while p < pkg_end:
                t, hs, sz = struct.unpack_from('<HHI', d, p)
                if t == 0x0201:
                    yield from type_chunk(d, p, hs, type_pool, key_pool)
                p += sz
        o += csize


def type_chunk(d, p, hs, type_pool, key_pool):
    tid, flags, _, count, estart = struct.unpack_from('<BBHII', d, p + 8)
    cfg = p + 20
    lang = d[cfg + 8:cfg + 10]
    lang = lang.decode('latin-1').rstrip('\0') if lang[0] < 0x80 else 'packed'
    if lang not in SHOWN_LANGS:
        return
    tname = type_pool.strings[tid - 1]
    sparse, off16 = flags & 0x01, flags & 0x02
    entries = []
    if sparse:
        for i in range(count):
            idx, off = struct.unpack_from('<HH', d, p + hs + 4 * i)
            entries.append(off * 4)
    elif off16:
        for i in range(count):
            off = struct.unpack_from('<H', d, p + hs + 2 * i)[0]
            if off != 0xffff:
                entries.append(off * 4)
    else:
        for i in range(count):
            off = struct.unpack_from('<I', d, p + hs + 4 * i)[0]
            if off != 0xffffffff:
                entries.append(off)
    for off in entries:
        e = p + estart + off
        esize, eflags = struct.unpack_from('<HH', d, e)
        if eflags & 0x08:  # compact entry: key u16, flags u16 (type in high byte), data u32
            key = esize
            if (eflags >> 8) == 0x03:
                yield struct.unpack_from('<I', d, e + 4)[0], f'{tname}/{key_pool.strings[key]}'
            continue
        key = struct.unpack_from('<I', d, e + 4)[0]
        name = f'{tname}/{key_pool.strings[key]}'
        if eflags & 0x01:
            n = struct.unpack_from('<I', d, e + 12)[0]
            for k in range(n):
                _, _, _, vtype, data = struct.unpack_from('<IHBBI', d, e + esize + 12 * k)
                if vtype == 0x03:
                    yield data, name
        else:
            _, _, vtype, data = struct.unpack_from('<HBBI', d, e + 8)
            if vtype == 0x03:
                yield data, name


def load(path):
    d = open(path, 'rb').read()
    _, hs, total, _ = struct.unpack_from('<HHII', d, 0)
    pool = Pool(d, hs)
    return d, hs, total, pool


def list_cmd(path, out):
    d, hs, total, pool = load(path)
    found = {}
    for idx, name in walk_values(d, hs + pool.size, total):
        s = pool.strings[idx]
        if CJK.search(s):
            found.setdefault(s, {'names': [], 'styled': idx < pool.styles})['names'].append(name)
    json.dump(found, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(found)} CJK strings visible to non-CJK locales')


def apply_cmd(path, map_json, out):
    d, hs, total, pool = load(path)
    table = json.load(open(map_json, encoding='utf-8'))
    targets = {idx for idx, _ in walk_values(d, hs + pool.size, total)}
    n = 0
    for idx in targets:
        s = pool.strings[idx]
        if s in table and idx >= pool.styles:
            pool.strings[idx] = table[s]; n += 1
    new_pool = pool.encode()
    rest = d[hs + pool.size:]
    head = bytearray(d[:hs])
    struct.pack_into('<I', head, 4, hs + len(new_pool) + len(rest))
    open(out, 'wb').write(bytes(head) + new_pool + rest)
    print(f'{n} pool strings replaced')


MANIFEST_TEXT = {
    '传奇一瞬 · 原厂模型实验': 'Legendary Moment · OEM model experiment',
    '徕卡风味版': 'Leica Flavor Edition',
    '徕卡一瞬': 'Leica Moment',
    '百变徕卡': 'Leica Styles',
    '徕卡一瞬·适配': 'Leica Moment · Compat',
}


def manifest_cmd(path, out):
    """Translate raw (non-resource) labels in binary AndroidManifest.xml."""
    d = open(path, 'rb').read()
    _, hs, _ = struct.unpack_from('<HHI', d, 0)
    pool = Pool(d, hs)
    pool.strings = [MANIFEST_TEXT.get(s, s) for s in pool.strings]
    left = [s for s in pool.strings if CJK.search(s)]
    if left:
        sys.exit(f'untranslated manifest strings: {left}')
    new_pool = pool.encode()
    rest = d[hs + pool.size:]
    head = bytearray(d[:hs])
    struct.pack_into('<I', head, 4, hs + len(new_pool) + len(rest))
    open(out, 'wb').write(bytes(head) + new_pool + rest)


if __name__ == '__main__':
    {'list': list_cmd, 'apply': apply_cmd, 'manifest': manifest_cmd}[sys.argv[1]](*sys.argv[2:])
