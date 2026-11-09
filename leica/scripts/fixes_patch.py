"""Smali fixes on top of patch_port.py.

  fixes_patch.py <smali_root> <classes3_smali> <java_smali>

1. RearLens.call() looks methods up through MethodCache instead of scanning getMethods() on every
   call while the RearLens class lock is held (the lens chip on the main thread waited on it: ANR).
2. ModeSelectView installs the "Leica Styles" mode entry from its constructor too. MIUI only calls
   setItems() on a cold start, so after Back/Home and relaunch the entry was missing.
3. Film-look LUT styles (FilmLut, ids 771..778) appended to the donor model gallery
   (ModelUi / ModelPort / CloudGalleryAdapter) and accepted by the Leica Styles editor.
"""
import os, re, shutil, sys

COUNT = 8                 # FilmLut.IDS
LAST = 770 + COUNT        # last style id
ADDED = 3 + COUNT         # donor models + film looks in the gallery
FILM = 'Lcom/codex/filmlut/FilmLut;'


def edit(path, pairs):
    src = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if src.count(old) != 1:
            sys.exit(f'{os.path.basename(path)}: anchor found {src.count(old)}x: {old.strip()[:60]!r}')
        src = src.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='\n').write(src)


def method(path, sig, pairs):
    """Apply replacements inside one method only."""
    src = open(path, encoding='utf-8').read()
    start = src.index(f'.method {sig}')
    end = src.index('.end method', start)
    body = src[start:end]
    for old, new in pairs:
        if body.count(old) != 1:
            sys.exit(f'{os.path.basename(path)} {sig}: anchor found {body.count(old)}x: {old.strip()!r}')
        body = body.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='\n').write(src[:start] + body + src[end:])


CALL = """.method static varargs call(Ljava/lang/Object;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/Object;
    .registers 5
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/lang/Exception;
        }
    .end annotation

    const/4 v0, 0x0

    if-nez p0, :have_target

    return-object v0

    :have_target
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v0

    array-length v1, p2

    invoke-static {v0, p1, v1}, Lcom/codex/rearlens/MethodCache;->find(Ljava/lang/Class;Ljava/lang/String;I)Ljava/lang/reflect/Method;

    move-result-object v0

    if-nez v0, :have_method

    return-object v0

    :have_method
    invoke-virtual {v0, p0, p2}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method"""


def rearlens(root):
    path = os.path.join(root, 'classes25/com/codex/rearlens/RearLens.smali')
    src = open(path, encoding='utf-8').read()
    m = re.search(r'\.method static varargs call\(.*?\.end method', src, re.S)
    if not m:
        sys.exit('RearLens.call not found')
    open(path, 'w', encoding='utf-8', newline='\n').write(src[:m.start()] + CALL + src[m.end():])


def mode_entry(classes3):
    path = os.path.join(classes3, 'com/android/camera/ui/ModeSelectView.smali')
    method(path, 'public constructor <init>(Landroid/content/Context;Landroid/util/AttributeSet;)V', [
        ('    return-void\n', '    invoke-static {p0}, Lcom/codex/editor/EditorEntry;->install(Landroid/view/View;)V\n\n    return-void\n')])


def extend(field, kind):
    return (f'    sput-object v0, Lcom/codex/modelport/ModelUi;->{field}:[Ljava/lang/String;\n',
            f'    const/4 v1, {kind}\n\n'
            f'    invoke-static {{v0, v1}}, {FILM}->extend([Ljava/lang/String;I)[Ljava/lang/String;\n\n'
            f'    move-result-object v0\n\n'
            f'    sput-object v0, Lcom/codex/modelport/ModelUi;->{field}:[Ljava/lang/String;\n')


def film_styles(root):
    ui = os.path.join(root, 'classes24/com/codex/modelport/ModelUi.smali')
    method(ui, 'static constructor <clinit>()V', [
        extend('NAMES', '0x0'), extend('FILES', '0x1'), extend('INTRO', '0x2'),
        ('    const/4 v0, 0x3\n', f'    const/16 v0, {hex(ADDED)}\n')])
    method(ui, 'static added(I)Z', [('const/4 v0, 0x4', f'const/16 v0, {hex(ADDED + 1)}')])
    method(ui, 'static previous(I)I', [('const/4 v0, 0x5', f'const/16 v0, {hex(ADDED + 2)}'),
                                        ('add-int/lit8 p0, p0, -0x3', f'add-int/lit8 p0, p0, -{hex(ADDED)}')])
    method(ui, 'public static galleryNames()[Ljava/lang/String;', [
        ('const/4 v2, 0x3', f'const/16 v2, {hex(ADDED)}'), ('const/4 v3, 0x5', f'const/16 v3, {hex(ADDED + 2)}')])
    method(ui, 'public static gallerySelection(Landroid/content/Context;I)I', [
        ('add-int/lit8 p0, p0, 0x3', f'add-int/lit8 p0, p0, {hex(ADDED)}')])
    method(ui, 'public static galleryIntro(Ljava/lang/String;)Ljava/lang/String;', [
        ('const/4 v1, 0x3', f'const/16 v1, {hex(ADDED)}')])

    port = os.path.join(root, 'classes24/com/codex/modelport/ModelPort.smali')
    method(port, 'public static valid(I)Z', [('const/16 v0, 0x302', f'const/16 v0, {hex(LAST)}')])
    method(port, 'public static process(Landroid/content/Context;[BI)[B', [
        ('    .line 17\n    invoke-static {p2}, Lcom/codex/modelport/ModelPort;->valid(I)Z\n',
         f'    invoke-static {{p2}}, {FILM}->owns(I)Z\n\n    move-result v0\n\n    if-eqz v0, :not_film\n\n'
         f'    invoke-static {{p0, p1, p2}}, {FILM}->process(Landroid/content/Context;[BI)[B\n\n'
         f'    move-result-object v0\n\n    return-object v0\n\n    :not_film\n'
         '    invoke-static {p2}, Lcom/codex/modelport/ModelPort;->valid(I)Z\n')])

    gallery = os.path.join(root, 'classes23/com/codex/fullm9/CloudGalleryAdapter.smali')
    method(gallery, 'static added(I)Z', [('const/4 v0, 0x4', f'const/16 v0, {hex(ADDED + 1)}')])
    method(gallery, 'static previous(I)I', [('const/4 v0, 0x5', f'const/16 v0, {hex(ADDED + 2)}'),
                                             ('add-int/lit8 p0, p0, -0x3', f'add-int/lit8 p0, p0, -{hex(ADDED)}')])
    method(gallery, 'public static selection(Landroid/content/Context;)I', [
        ('add-int/lit8 p0, p0, 0x3', f'add-int/lit8 p0, p0, {hex(ADDED)}')])

    editor = os.path.join(root, 'classes26/com/codex/editor/EditorRenderer.smali')
    edit(editor, [('const/16 v2, 0x302', f'const/16 v2, {hex(LAST)}')])


def main(root, classes3, java_smali):
    for rel, dex in (('com/codex/filmlut', 'classes24'), ('com/codex/rearlens/MethodCache.smali', 'classes25')):
        src, dst = os.path.join(java_smali, rel), os.path.join(root, dex, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy(src, dst)
    rearlens(root)
    mode_entry(classes3)
    film_styles(root)
    print(f'fixes: method cache, mode entry, {COUNT} film LUT styles')


if __name__ == '__main__':
    main(*sys.argv[1:])
