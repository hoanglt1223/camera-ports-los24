"""Apply the gauguin patches to a baksmali tree and the profile catalog.

  patch_port.py <smali_root> <device-profiles.json in> <out json> <resources.arsc in> <out arsc>
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arsc_strings, smali_strings  # noqa: E402

PROFILES = 'Lcom/codex/modelmatch/Profiles;'
PROFILE = 'Lcom/codex/modelmatch/Profiles$Profile;'

# With no saved choice, select the catalog entry whose codes match Build.MODEL/DEVICE
# (Profiles.detected() exists in the port but nothing calls it).
AUTO_DETECT_OLD = """    :goto_93
    const/4 p0, 0x1
"""
AUTO_DETECT_NEW = f"""    :goto_93
    invoke-virtual {{p0}}, Ljava/lang/String;->length()I

    move-result v2

    if-nez v2, :gauguin_auto_done

    sget-object v2, {PROFILES}->selected:{PROFILE}

    if-nez v2, :gauguin_auto_done

    invoke-static {{}}, {PROFILES}->detected(){PROFILE}

    move-result-object v2

    sput-object v2, {PROFILES}->selected:{PROFILE}

    :gauguin_auto_done
    const/4 p0, 0x1
"""

# The QNN/HTP experiment screen cannot load its DSP graph on SM7225; hide its entry button.
EXPERIMENT_OLD = """    invoke-virtual {v13, v0}, Landroid/widget/Button;->setText(Ljava/lang/CharSequence;)V
"""
EXPERIMENT_NEW = EXPERIMENT_OLD + """
    const/16 v0, 0x8

    invoke-virtual {v13, v0}, Landroid/view/View;->setVisibility(I)V
"""


# ProfileRouter.logicalPaths() only offers zoom stops through logical cameras or cameras whose
# zoom range starts below 1x. gauguin's main (id 0) is neither, so a profile stop with no
# physical lens (the 2x crop) was dropped. Let the main camera itself carry such a stop.
CROP_STOP_OLD = """    invoke-interface {v7}, Ljava/util/Set;->isEmpty()Z

    move-result v10

    if-eqz v10, :cond_64
"""
CROP_STOP_NEW = """    invoke-virtual {v8, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v10

    if-nez v10, :cond_64

""" + CROP_STOP_OLD


NOTE = '固定倍率采用公开标识；未取得可靠公开焦距或倍率时由本机镜头参数补齐。只有元数据可读不代表已经调用成功。'
# Longest phrases first; applied to profile names, aliases and notes shown in the model picker.
PROFILE_TEXT = [
    (NOTE + ' 本机保留兼容路由，避免新增辅助ID进入原生会话。',
     'Fixed stops follow published labels; unknown focal lengths are filled from this phone\'s lens data. '
     'Readable metadata does not mean the lens can be opened. Keeps the compatibility route so new aux IDs '
     'stay out of the native session.'),
    (NOTE + ' 独立微距等辅助镜头不列为普通变焦停点。',
     'Fixed stops follow published labels; unknown focal lengths are filled from this phone\'s lens data. '
     'Readable metadata does not mean the lens can be opened. Separate macro and other aux lenses are not zoom stops.'),
    (NOTE, 'Fixed stops follow published labels; unknown focal lengths are filled from this phone\'s lens data. '
           'Readable metadata does not mean the lens can be opened.'),
    ('超抗摔金刚石旗舰手机', 'rugged diamond flagship'),
    ('参数 | OPPO 官方网站', 'specs | OPPO official site'),
    ('卫星通信版', 'Satellite Edition'), ('天玑版', 'Dimensity Edition'), ('活力版', 'Vitality Edition'),
    ('电竞版', 'Gaming Edition'), ('极速版', 'Speed Edition'), ('系列', 'Series'),
    (' 手机', ''), ('超 ', 'Super '), ('小米', 'Xiaomi'),
]
TRANSLATED_KEYS = {'name', 'aliases', 'note'}


def translate_profiles(catalog):
    def tr(s):
        for zh, en in PROFILE_TEXT:
            s = s.replace(zh, en)
        return s
    for p in catalog['profiles']:
        for k in TRANSLATED_KEYS & p.keys():
            p[k] = [tr(v) for v in p[k]] if isinstance(p[k], list) else tr(p[k])


def patch(path, old, new):
    src = open(path, encoding='utf-8').read()
    if src.count(old) != 1:
        sys.exit(f'patch anchor not unique in {path}: {src.count(old)}')
    open(path, 'w', encoding='utf-8', newline='\n').write(src.replace(old, new))


def main(root, json_in, json_out, arsc_in, arsc_out):
    arsc_strings.apply_cmd(arsc_in, os.path.join(HERE, 'arsc-translations-en.json'), arsc_out)
    patch(os.path.join(root, 'classes30/com/codex/modelmatch/Profiles.smali'), AUTO_DETECT_OLD, AUTO_DETECT_NEW)
    patch(os.path.join(root, 'classes11/com/codex/leicaapp/LeicaV43Ui.smali'), EXPERIMENT_OLD, EXPERIMENT_NEW)
    patch(os.path.join(root, 'classes30/com/codex/rearlens/ProfileRouter.smali'), CROP_STOP_OLD, CROP_STOP_NEW)
    smali_strings.apply(root, os.path.join(HERE, 'translations-en.json'))

    catalog = json.load(open(json_in, encoding='utf-8'))
    entry = json.load(open(os.path.join(HERE, 'gauguin-profile.json'), encoding='utf-8'))
    translate_profiles(catalog)
    catalog['profiles'] = [p for p in catalog['profiles'] if p['id'] != entry['id']] + [entry]
    with open(json_out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=2)
    print(f"profiles: {len(catalog['profiles'])}")


if __name__ == '__main__':
    main(*sys.argv[1:])
