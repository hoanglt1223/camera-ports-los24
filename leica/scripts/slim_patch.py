"""Smali patch for the -Slim build: serve donor120's leica-v4 models from assets/lm_leica-v4.

  slim_patch.py <smali_root>

assets/donor120/leica-v4 is byte-identical (CRC) to the matching files in assets/lm_leica-v4,
so ModelAssets maps "donor120/leica-v4/..." there instead of shipping a third copy. The
dsp/ Hexagon HTP V79/V81 skeletons are dropped from the APK (SM7225 has no HTP), so the
SHARED entry that pulled leica-v4/dsp/libQnnHtpV81.so into donor120 is retired too.
"""
import os, sys

CLASS = 'Lcom/codex/modelport/ModelAssets;'
BASE = f'{CLASS}->base(Ljava/lang/String;)Ljava/lang/String;'

SHARED_OLD = '    const-string v3, "leica-v4/dsp/libQnnHtpV81.so"\n'
SHARED_NEW = '    const-string v3, "leica-v4/styletrans_params.json"\n'

PREFIX_OLD = """    const-string v1, "donor120/"

    invoke-direct {v0, v1}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
"""


def prefix_new(reg):
    return f"""    invoke-static {{{reg}}}, {BASE}

    move-result-object v1

    invoke-direct {{v0, v1}}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
"""


BASE_METHOD = """
.method static base(Ljava/lang/String;)Ljava/lang/String;
    .registers 2

    const-string v0, "leica-v4"

    invoke-virtual {p0, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v0

    if-eqz v0, :donor

    const-string v0, "lm_"

    return-object v0

    :donor
    const-string v0, "donor120/"

    return-object v0
.end method
"""


def sub_method(src, name, old, new):
    start = src.index(f'.method {name}')
    end = src.index('.end method', start)
    body = src[start:end]
    if body.count(old) != 1:
        sys.exit(f'ModelAssets.{name}: anchor not found exactly once')
    return src[:start] + body.replace(old, new) + src[end:]


def main(root):
    path = os.path.join(root, 'classes24', 'com', 'codex', 'modelport', 'ModelAssets.smali')
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    if src.count(SHARED_OLD) != 1:
        sys.exit('ModelAssets.<clinit>: SHARED dsp entry not found')
    src = src.replace(SHARED_OLD, SHARED_NEW)
    src = sub_method(src, 'public static list(', PREFIX_OLD, prefix_new('p1'))
    src = sub_method(src, 'static path(', PREFIX_OLD, prefix_new('p0'))
    src += BASE_METHOD
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(src)
    print('slim: ModelAssets redirected donor120/leica-v4 -> lm_leica-v4')


if __name__ == '__main__':
    main(sys.argv[1])
