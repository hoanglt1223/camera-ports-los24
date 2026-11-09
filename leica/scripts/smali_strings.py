"""Helpers for smali string literals plus the CJK -> English map builder/applier.

  smali_strings.py build <cjk-strings.json> <translations-en.tsv> <out translations-en.json>
  smali_strings.py apply <smali_root> <translations-en.json>
"""
import glob, json, os, re, sys

CONST = re.compile(r'(const-string(?:/jumbo)? [vp]\d+, )("(?:[^"\\]|\\.)*")')
CJK = re.compile(r'[　-鿿＀-￯]')


def decode(lit):
    body = lit[1:-1]
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c != '\\':
            out.append(c); i += 1; continue
        n = body[i + 1]
        if n == 'u':
            out.append(chr(int(body[i + 2:i + 6], 16))); i += 6
        else:
            out.append({'n': '\n', 't': '\t', 'r': '\r', '"': '"', "'": "'", '\\': '\\', 'b': '\b', 'f': '\f'}[n]); i += 2
    return ''.join(out)


def encode(text):
    out = []
    for c in text:
        if c == '\n': out.append('\\n')
        elif c == '\t': out.append('\\t')
        elif c == '"': out.append('\\"')
        elif c == '\\': out.append('\\\\')
        elif 0x20 <= ord(c) < 0x7f: out.append(c)
        else: out.append('\\u%04x' % ord(c))
    return '"' + ''.join(out) + '"'


def build(cjk_json, tsv, out):
    keys = list(json.load(open(cjk_json, encoding='utf-8')).keys())
    table = {}
    for line in open(tsv, encoding='utf-8'):
        line = line.rstrip('\r\n')
        if not line:
            continue
        idx, _, en = line.partition('\t')
        zh = decode(keys[int(idx)])
        en = en.replace('\\n', '\n').strip(' ')
        # editors strip edge spaces; take them from the source literal, which is concatenated at runtime
        lead = zh[:len(zh) - len(zh.lstrip(' '))]
        trail = zh[len(zh.rstrip(' ')):]
        if not trail and zh.endswith('：') and en.endswith(':'):
            trail = ' '
        table[zh] = lead + en + trail
    json.dump(table, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(table)} of {len(keys)} strings mapped')


def apply(root, table_json):
    table = json.load(open(table_json, encoding='utf-8'))
    changed = files = 0
    left = set()

    def sub(m):
        nonlocal changed
        text = decode(m.group(2))
        if text in table:
            changed += 1
            return m.group(1) + encode(table[text])
        if CJK.search(text):
            left.add(text)
        return m.group(0)

    for f in glob.glob(os.path.join(root, '**', '*.smali'), recursive=True):
        src = open(f, encoding='utf-8').read()
        dst = CONST.sub(sub, src)
        if dst != src:
            files += 1
            open(f, 'w', encoding='utf-8', newline='\n').write(dst)
    print(f'{changed} literals replaced in {files} files; {len(left)} CJK literals left')
    for t in sorted(left):
        print('  left:', t.encode('unicode_escape').decode())


if __name__ == '__main__':
    {'build': build, 'apply': apply}[sys.argv[1]](*sys.argv[2:])
