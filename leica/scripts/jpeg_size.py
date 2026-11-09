"""Print JPEG pixel size from the first SOF marker: jpeg_size.py <file>..."""
import struct, sys

for path in sys.argv[1:]:
    d = open(path, 'rb').read()
    o = 2
    while o < len(d):
        marker, length = d[o + 1], struct.unpack('>H', d[o + 2:o + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack('>HH', d[o + 5:o + 9])
            print(path, f'{w}x{h}', len(d))
            break
        o += 2 + length
