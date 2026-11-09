"""List CJK const-strings in baksmali output: collect_cjk.py <smali_root> <out.json>"""
import collections, glob, json, os, re, sys

CONST = re.compile(r'const-string(?:/jumbo)? [vp]\d+, ("(?:[^"\\]|\\.)*")')
CJK = re.compile(r'[　-鿿＀-￯]|\\u(?:[4-9][0-9a-f]{3}|3[0-9a-f]{3}|ff[0-9a-f]{2})')

root, out = sys.argv[1], sys.argv[2]
found = collections.OrderedDict()
for f in sorted(glob.glob(os.path.join(root, '**', '*.smali'), recursive=True)):
    rel = os.path.relpath(f, root).replace('\\', '/')
    with open(f, encoding='utf-8') as fh:
        for line in fh:
            m = CONST.search(line)
            if m and CJK.search(m.group(1)):
                found.setdefault(m.group(1), set()).add(rel)
with open(out, 'w', encoding='utf-8') as fh:
    json.dump({k: sorted(v) for k, v in found.items()}, fh, ensure_ascii=False, indent=0)
print(len(found))
