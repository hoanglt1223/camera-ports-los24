"""Copy an APK, replacing selected entries and dropping the old signature.

  repack_apk.py <in.apk> <out.apk> <entry=file | --drop=prefix | --add=entry=file> [...]
"""
import shutil, sys, zipfile

src, dst, *pairs = sys.argv[1:]
drop = tuple(p[7:] for p in pairs if p.startswith('--drop='))
add = dict(p[6:].split('=', 1) for p in pairs if p.startswith('--add='))
repl = dict(p.split('=', 1) for p in pairs if not p.startswith(('--drop=', '--add=')))
dropped = 0
seen = set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w', allowZip64=False) as zout:
    for info in zin.infolist():
        name = info.filename
        if name.startswith('META-INF/') and name.rsplit('.', 1)[-1].upper() in ('SF', 'RSA', 'DSA', 'EC', 'MF'):
            continue
        if drop and name.startswith(drop):
            dropped += 1
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
    for name, path in add.items():
        if name in zin.namelist():
            sys.exit(f'already in apk: {name}')
        zout.write(path, name, zipfile.ZIP_DEFLATED)
missing = set(repl) - seen
if missing:
    sys.exit(f'entries not found: {sorted(missing)}')
print(f'replaced {len(seen)} entries, added {len(add)}, dropped {dropped}')
