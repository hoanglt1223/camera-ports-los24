"""Smali patch for the iqooneo11 build: run the M9/M3 style nets on the SM8750 (HTP V79) DSP.

  iqoo_patch.py <smali_root>

The APK carries one self-consistent HTP V79 kit, QNN 2.33.0: libzxyletrans_runner.so ->
libzxalgo_styletrans.so -> libzxnHtp/libzxnSystem, preloading libzxnHtpV81Stub.so (despite the
name it is the V79 stub, SONAME libQnnHtpV79Stub.so) with the V79 skel and V79 context binaries
from lm_leica-v4. The leicaapp runner (libQnnHtp 2.33.104 + real V81 stub/skel) and the model120
runner (loads the stock 2.33.104 libmialgo_styletrans next to the 2.33.0 V79 stub) cannot open a
V79 HTP session, so both are pointed at the zx runner. build-leica-gauguin.ps1 -Target iqooneo11
also swaps assets/leica-v4 to the V79 context binaries and skel.
"""
import os, sys

RUNNERS = [
    ('classes11/com/codex/leicaapp/LegendaryPostProcessor.smali', '/libstyletrans_runner.so'),
    ('classes24/com/codex/model120/LegendaryPostProcessor.smali', '/libd12letrans_runner.so'),
]
ZX = '/libzxyletrans_runner.so'


def main(root):
    for rel, old in RUNNERS:
        path = os.path.join(root, rel)
        src = open(path, encoding='utf-8').read()
        anchor = f'const-string v3, "{old}"'
        if src.count(anchor) != 1:
            sys.exit(f'{rel}: runner anchor found {src.count(anchor)} times')
        open(path, 'w', encoding='utf-8', newline='\n').write(src.replace(anchor, f'const-string v3, "{ZX}"'))
    print('iqoo: style runners -> libzxyletrans_runner.so (HTP V79 kit)')


if __name__ == '__main__':
    main(sys.argv[1])
