"""Copy an APK, replacing selected entries and dropping the old signature.

  repack_apk.py <in.apk> <out.apk> <entry=file> [<entry=file> ...]
"""
import shutil, sys, zipfile

src, dst, *pairs = sys.argv[1:]
repl = dict(p.split('=', 1) for p in pairs)
seen = set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w', allowZip64=False) as zout:
    for info in zin.infolist():
        name = info.filename
        if name.startswith('META-INF/') and name.rsplit('.', 1)[-1].upper() in ('SF', 'RSA', 'DSA', 'EC', 'MF'):
            continue
        out = zipfile.ZipInfo(name, date_time=info.date_time)
        out.compress_type = info.compress_type
        out.external_attr = info.external_attr
        if name in repl:
            seen.add(name)
            with open(repl[name], 'rb') as fh:
                zout.writestr(out, fh.read())
        else:
            with zin.open(info) as fi, zout.open(out, 'w') as fo:
                shutil.copyfileobj(fi, fo, 1 << 20)
missing = set(repl) - seen
if missing:
    sys.exit(f'entries not found: {sorted(missing)}')
print(f'replaced {len(seen)} entries')
