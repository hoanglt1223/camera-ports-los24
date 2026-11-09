"""Generate the film-look 3D LUTs added to Leica Styles, plus their gallery thumbnails.

  film_luts.py <out_dir> <sample.jpg>

Writes <out_dir>/donor120/film/<id>.bin (the AlexaLut format: 65^3 float32 little-endian,
planar R then G then B, index = b*65*65 + g*65 + r, grid points at k/64) and
<out_dir>/model120-intro/<id>.jpg (1536x1024 crop of the sample with the LUT applied).
Every look is built here from simple tone/colour operations; no third-party LUT data.
"""
import math, os, struct, sys

from PIL import Image

N = 65


def clamp(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def luma(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def scurve(x, k):
    """Contrast around mid-grey; k > 0 adds contrast, k < 0 flattens."""
    y = x + k * x * (1 - x) * (2 * x - 1) * -2
    return clamp(y)


def sat(r, g, b, s):
    y = luma(r, g, b)
    return y + (r - y) * s, y + (g - y) * s, y + (b - y) * s


def lift_gain(x, lift, gain):
    return clamp(lift + x * (gain - lift))


def split_tone(r, g, b, shadow, highlight, amount):
    y = luma(r, g, b)
    ws, wh = (1 - y) ** 2, y ** 2
    return (r + amount * (ws * shadow[0] + wh * highlight[0]),
            g + amount * (ws * shadow[1] + wh * highlight[1]),
            b + amount * (ws * shadow[2] + wh * highlight[2]))


def warm_film(r, g, b):
    r, g, b = r * 1.06, g * 1.01, b * 0.90
    r, g, b = (scurve(c, 0.18) for c in (r, g, b))
    r, g, b = sat(r, g, b, 0.92)
    return (lift_gain(c, 0.035, 0.98) for c in (r, g, b))


def cool_chrome(r, g, b):
    r, g, b = r * 0.95, g * 0.99, b * 1.06
    r, g, b = (scurve(c, 0.30) for c in (r, g, b))
    y = luma(r, g, b)
    s = 0.80 + 0.35 * max(0.0, b - max(r, g))  # keep blues, mute the rest
    return sat(r, g, b, s)


def mono(r, g, b, wr, wg, wb, k, tone):
    y = clamp(wr * r + wg * g + wb * b)
    y = scurve(y, k)
    return clamp(y + tone[0] * y * (1 - y)), clamp(y + tone[1] * y * (1 - y)), clamp(y + tone[2] * y * (1 - y))


def mono_contrast(r, g, b):
    return mono(r, g, b, 0.45, 0.45, 0.10, 0.45, (0, 0, 0))


def mono_soft(r, g, b):
    r, g, b = mono(r, g, b, 0.30, 0.59, 0.11, -0.10, (0.06, 0.02, -0.04))
    return (lift_gain(c, 0.05, 0.96) for c in (r, g, b))


def faded_matte(r, g, b):
    r, g, b = (scurve(c, 0.10) for c in (r, g, b))
    r, g, b = sat(r, g, b, 0.72)
    r, g, b = split_tone(r, g, b, (-0.02, 0.01, 0.04), (0.03, 0.01, -0.02), 0.6)
    return (lift_gain(c, 0.10, 0.92) for c in (r, g, b))


def portrait_film(r, g, b):
    r, g, b = r * 1.03, g * 1.00, b * 0.96
    r, g, b = (scurve(c, -0.08) for c in (r, g, b))
    y = luma(r, g, b)
    # pastel greens, gently warmer midtones
    g2 = g - 0.04 * max(0.0, g - max(r, b))
    r, g, b = sat(r, g2, b, 0.88)
    r, g, b = split_tone(r, g, b, (0.0, 0.01, 0.02), (0.03, 0.015, -0.01), 0.7)
    return (lift_gain(c, 0.03, 0.99) for c in (r, g, b))


def teal_orange(r, g, b):
    r, g, b = (scurve(c, 0.22) for c in (r, g, b))
    r, g, b = split_tone(r, g, b, (-0.06, 0.02, 0.06), (0.07, 0.02, -0.06), 0.9)
    return sat(r, g, b, 1.05)


def vivid_slide(r, g, b):
    r, g, b = (scurve(c, 0.32) for c in (r, g, b))
    r, g, b = sat(r, g, b, 1.30)
    return (lift_gain(c, -0.01, 1.0) for c in (r, g, b))


LOOKS = [
    ('film-warm', warm_film), ('film-chrome', cool_chrome), ('film-mono-hc', mono_contrast),
    ('film-matte', faded_matte), ('film-portrait', portrait_film), ('film-teal-orange', teal_orange),
    ('film-mono-soft', mono_soft), ('film-vivid', vivid_slide),
]


def build(fn):
    planes = ([0.0] * N ** 3, [0.0] * N ** 3, [0.0] * N ** 3)
    for bi in range(N):
        for gi in range(N):
            base = bi * N * N + gi * N
            for ri in range(N):
                o = tuple(clamp(c) for c in fn(ri / 64.0, gi / 64.0, bi / 64.0))
                for p in range(3):
                    planes[p][base + ri] = o[p]
    return planes


def apply(img, planes):
    # sample at 17^3 via PIL's own 3D LUT filter (thumbnail only)
    from PIL import ImageFilter
    size, table = 17, []
    for bi in range(size):
        for gi in range(size):
            for ri in range(size):
                idx = round(bi * 64 / 16) * N * N + round(gi * 64 / 16) * N + round(ri * 64 / 16)
                table += [planes[0][idx], planes[1][idx], planes[2][idx]]
    return img.filter(ImageFilter.Color3DLUT(size, table))


def main(out, sample):
    lut_dir, intro_dir = os.path.join(out, 'donor120', 'film'), os.path.join(out, 'model120-intro')
    os.makedirs(lut_dir, exist_ok=True)
    os.makedirs(intro_dir, exist_ok=True)
    src = Image.open(sample).convert('RGB')
    w, h = src.size
    scale = max(1536 / w, 1024 / h)
    src = src.resize((math.ceil(w * scale), math.ceil(h * scale)), Image.LANCZOS)
    left, top = (src.width - 1536) // 2, (src.height - 1024) // 2
    src = src.crop((left, top, left + 1536, top + 1024))
    for name, fn in LOOKS:
        planes = build(fn)
        with open(os.path.join(lut_dir, name + '.bin'), 'wb') as fh:
            for p in planes:
                fh.write(struct.pack('<%df' % len(p), *p))
        apply(src, planes).save(os.path.join(intro_dir, name + '.jpg'), quality=88)
    print(f'film luts: {len(LOOKS)}')


if __name__ == '__main__':
    main(*sys.argv[1:])
