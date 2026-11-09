"""List text assets in an APK that contain CJK string values: scan_assets_cjk.py <apk> [entry]"""
import re, sys, zipfile

QUOTED = re.compile(r'"([^"\n]*[㐀-鿿][^"\n]*)"|>([^<\n]*[㐀-鿿][^<\n]*)<')
z = zipfile.ZipFile(sys.argv[1])
for i in z.infolist():
    n = i.filename
    if len(sys.argv) > 2 and n != sys.argv[2]:
        continue
    if n.startswith('assets/') and n.endswith(('.json', '.xml', '.txt', '.properties', '.csv')) and i.file_size < 8_000_000:
        vals = {a or b for a, b in QUOTED.findall(z.read(n).decode('utf-8', 'ignore'))}
        if vals:
            print(len(vals), n, i.file_size)
            if len(sys.argv) > 2:
                for v in sorted(vals):
                    print('  ', v.encode('unicode_escape').decode() if False else v)
