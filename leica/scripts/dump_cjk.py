"""Print collected strings decoded, one per line: index<TAB>class<TAB>text"""
import json, sys

data = json.load(open(sys.argv[1], encoding='utf-8'))
with open(sys.argv[2], 'w', encoding='utf-8') as out:
    for i, (lit, files) in enumerate(data.items()):
        text = lit[1:-1].encode('utf-8').decode('unicode_escape').encode('latin-1').decode('utf-8') \
            if '\\u' not in lit else lit[1:-1].encode('latin-1', 'backslashreplace').decode('unicode_escape')
        cls = ','.join(sorted({f.split('/')[-1][:-6] for f in files}))[:60]
        out.write(f'{i}\t{cls}\t{text!r}\n')
