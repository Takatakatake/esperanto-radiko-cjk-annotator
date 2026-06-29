# -*- coding: utf-8 -*-
"""
置換用JSON生成ロジックを、Streamlit生成ページ
「エスペラント文(漢字)置換用のJSONファイル生成ページ.py」の
ボタンブロック(行38-895)から忠実に移植したスタンドアロン版。
アプリ同梱モジュール(esp_replacement_json_make_module)の関数をそのまま再利用する。

generate(...) を呼ぶと combined_data(dict) を返す(JSONには書かない)。
呼び出し側で必要なら書き出す。
"""
import re, json, sys, os
from io import StringIO

def lp(path):
    if path.startswith('\\\\?\\'): return path
    if path.startswith('\\\\'): return '\\\\?\\UNC' + path[1:]
    if len(path) > 2 and path[1] == ':': return '\\\\?\\' + path
    return path

def import_placeholders(filename):
    with open(lp(filename), 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

# ---- 生成ページ 行38-44 の固定変数 (verbatim) ----
verb_suffix_2l={'as':'as', 'is':'is', 'os':'os', 'us':'us','at':'at','it':'it','ot':'ot', 'ad':'ad','iĝ':'iĝ','ig':'ig','ant':'ant','int':'int','ont':'ont'}
AN=[['dietan', '/diet/an/', '/diet/an'], ['afrikan', '/afrik/an/', '/afrik/an'], ['movadan', '/mov/ad/an/', '/mov/ad/an'], ['akcian', '/akci/an/', '/akci/an'], ['montaran', '/mont/ar/an/', '/mont/ar/an'], ['amerikan', '/amerik/an/', '/amerik/an'], ['regnan', '/regn/an/', '/regn/an'], ['dezertan', '/dezert/an/', '/dezert/an'], ['asocian', '/asoci/an/', '/asoci/an'], ['insulan', '/insul/an/', '/insul/an'], ['azian', '/azi/an/', '/azi/an'], ['ŝtatan', '/ŝtat/an/', '/ŝtat/an'], ['doman', '/dom/an/', '/dom/an'], ['montan', '/mont/an/', '/mont/an'], ['familian', '/famili/an/', '/famili/an'], ['urban', '/urb/an/', '/urb/an'], ['popolan', '/popol/an/', '/popol/an'], ['dekan', '/dekan/', '/dek/an'], ['partian', '/parti/an/', '/parti/an'], ['lokan', '/lok/an/', '/lok/an'], ['ŝipan', '/ŝip/an/', '/ŝip/an'], ['eklezian', '/eklezi/an/', '/eklezi/an'], ['landan', '/land/an/', '/land/an'], ['orientan', '/orient/an/', '/orient/an'], ['lernejan', '/lern/ej/an/', '/lern/ej/an'], ['enlandan', '/en/land/an/', '/en/land/an'], ['kalkan', '/kalkan/', '/kalk/an'], ['estraran', '/estr/ar/an/', '/estr/ar/an'], ['etnan', '/etn/an/', '/etn/an'], ['eŭropan', '/eŭrop/an/', '/eŭrop/an'], ['fazan', '/fazan/', '/faz/an'], ['polican', '/polic/an/', '/polic/an'], ['socian', '/soci/an/', '/soci/an'], ['societan', '/societ/an/', '/societ/an'], ['grupan', '/grup/an/', '/grup/an'], ['ligan', '/lig/an/', '/lig/an'], ['nacian', '/naci/an/', '/naci/an'], ['koran', '/koran/', '/kor/an'], ['religian', '/religi/an/', '/religi/an'], ['kuban', '/kub/an/', '/kub/an'], ['majoran', '/major/an/', '/major/an'], ['nordan', '/nord/an/', '/nord/an'], ['paran', 'paran', '/par/an'], ['parizan', '/pariz/an/', '/pariz/an'], ['parokan', '/parok/an/', '/parok/an'], ['podian', '/podi/an/', '/podi/an'], ['rusian', '/rus/i/an/', '/rus/ian'], ['satan', '/satan/', '/sat/an'], ['sektan', '/sekt/an/', '/sekt/an'], ['senatan', '/senat/an/', '/senat/an'], ['skisman', '/skism/an/', '/skism/an'], ['sudan', 'sudan', '/sud/an'], ['utopian', '/utopi/an/', '/utopi/an'], ['vilaĝan', '/vilaĝ/an/', '/vilaĝ/an'], ['arĝentan', '/arĝent/an/', '/arĝent/an']]
ON=[['duon', '/du/on/', '/du/on'], ['okon', '/ok/on/', '/ok/on'], ['nombron', '/nombr/on/', '/nombr/on'], ['patron', '/patron/', '/patr/on'], ['karbon', '/karbon/', '/karb/on'], ['ciklon', '/ciklon/', '/cikl/on'], ['aldon', '/al/don/', '/ald/on'], ['balon', '/balon/', '/bal/on'], ['baron', '/baron/', '/bar/on'], ['baston', '/baston/', '/bast/on'], ['magneton', '/magnet/on/', '/magnet/on'], ['beton', 'beton', '/bet/on'], ['bombon', '/bombon/', '/bomb/on'], ['breton', 'breton', '/bret/on'], ['burĝon', '/burĝon/', '/burĝ/on'], ['centon', '/cent/on/', '/cent/on'], ['milon', '/mil/on/', '/mil/on'], ['kanton', '/kanton/', '/kant/on'], ['citron', '/citron/', '/citr/on'], ['platon', 'platon', '/plat/on'], ['dekon', '/dek/on/', '/dek/on'], ['kvaron', '/kvar/on/', '/kvar/on'], ['kvinon', '/kvin/on/', '/kvin/on'], ['seson', '/ses/on/', '/ses/on'], ['trion', '/tri/on/', '/tri/on'], ['karton', '/karton/', '/kart/on'], ['foton', '/fot/on/', '/fot/on'], ['peron', '/peron/', '/per/on'], ['elektron', '/elektr/on/', '/elektr/on'], ['drakon', 'drakon', '/drak/on'], ['mondon', '/mon/don/', '/mond/on'], ['pension', '/pension/', '/pensi/on'], ['ordon', '/ordon/', '/ord/on'], ['eskadron', 'eskadron', '/eskadr/on'], ['senton', '/sen/ton/', '/sent/on'], ['eston', 'eston', '/est/on'], ['fanfaron', '/fanfaron/', '/fanfar/on'], ['feston', '/feston/', '/fest/on'], ['flegmon', 'flegmon', '/flegm/on'], ['fronton', '/fronton/', '/front/on'], ['galon', '/galon/', '/gal/on'], ['mason', '/mason/', '/mas/on'], ['helikon', 'helikon', '/helik/on'], ['kanon', '/kanon/', '/kan/on'], ['kapon', '/kapon/', '/kap/on'], ['kokon', '/kokon/', '/kok/on'], ['kolon', '/kolon/', '/kol/on'], ['komision', '/komision/', '/komisi/on'], ['salon', '/salon/', '/sal/on'], ['ponton', '/ponton/', '/pont/on'], ['koton', '/koton/', '/kot/on'], ['kripton', 'kripton', '/kript/on'], ['kupon', '/kupon/', '/kup/on'], ['lakon', 'lakon', '/lak/on'], ['ludon', '/lu/don/', '/lud/on'], ['melon', '/melon/', '/mel/on'], ['menton', '/menton/', '/ment/on'], ['milion', '/milion/', '/mili/on'], ['milionon', '/milion/on/', '/milion/on'], ['naŭon', '/naŭ/on/', '/naŭ/on'], ['violon', '/violon/', '/viol/on'], ['trombon', '/trombon/', '/tromb/on'], ['senson', '/sen/son/', '/sens/on'], ['sepon', '/sep/on/', '/sep/on'], ['skadron', 'skadron', '/skadr/on'], ['stadion', '/stadion/', '/stadi/on'], ['tetraon', 'tetraon', '/tetra/on'], ['timon', '/timon/', '/tim/on'], ['valon', 'valon', '/val/on']]
allowed_values = {-1, "-1", "ー１", "ー1", "-１", "－１", "－1"}
# 純粋な文法語尾(名詞o類・形容詞a類・副詞e類・対格n・複数j)。custom_stemmingでリテラル付加する。
_GRAM_ENDINGS = {"o","oj","on","ojn","a","aj","an","ajn","e","en","n","j","jn"}
# ハイフン直後のエスペラント文字を大文字化(固有名詞 Abu-Dabi 等。実テキストは各部大文字)
def _cap_after_hyphen(s):
    return re.sub(r'-([a-zĉĝĥĵŝŭ])', lambda m: '-' + m.group(1).upper(), s)
suffix_2char_roots=['ad', 'ag', 'am', 'ar', 'as', 'at', 'av', 'di', 'ec', 'eg', 'ej', 'em', 'er', 'et', 'id', 'ig', 'il', 'in', 'ir', 'is', 'it', 'lu', 'nj', 'op', 'or', 'os', 'ot', 'ov', 'pi', 'te', 'uj', 'ul', 'um', 'us', 'uz','ĝu','aĵ','iĝ','aĉ','aĝ','ŝu','eĥ']
prefix_2char_roots=['al', 'am', 'av', 'bo', 'di', 'du', 'ek', 'el', 'en', 'fi', 'ge', 'ir', 'lu', 'ne', 'ok', 'or', 'ov', 'pi', 're', 'te', 'uz','ĝu','aĉ','aĝ','ŝu','eĥ']
standalone_2char_roots=['al', 'ci', 'da', 'de', 'di', 'do', 'du', 'el', 'en', 'fi', 'ha', 'he', 'ho', 'ia', 'ie', 'io', 'iu', 'ja', 'je', 'ju','ke', 'la', 'li', 'mi', 'ne', 'ni', 'nu', 'ok', 'ol', 'po', 'se', 'si', 've', 'vi','ŭa','aŭ','ĉe','ĝi','ŝi','ĉu']


def generate(app_module_dir, data_dir, csv_path, stemming_json_path,
             user_repl_json_path, estem_path, rootlist_path,
             format_type='HTML格式_Ruby文字_大小调整', word_anno=None,
             use_parallel=False, num_processes=4):
    import pandas as pd
    sys.path.insert(0, app_module_dir)
    from esp_replacement_json_make_module import (
        convert_to_circumflex, output_format, capitalize_ruby_and_rt,
        remove_redundant_ruby_if_identical, safe_replace as mod_safe_replace,
        parallel_build_pre_replacements_dict,
    )
    # safe_replace は (old,new,placeholder) を使う版が必要。モジュールの safe_replace は3要素対応。
    safe_replace = mod_safe_replace
    _LATIN = re.compile(r'^[a-zĉĝĥĵŝŭ!\-]+$')

    imported_placeholders_for_global_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_global.txt'))
    imported_placeholders_for_2char_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_2char.txt'))
    imported_placeholders_for_local_replacement = import_placeholders(os.path.join(data_dir, 'placeholders_local.txt'))

    with open(lp(os.path.join(data_dir, 'char_widths.json')), 'r', encoding='utf-8') as fp:
        char_widths_dict = json.load(fp)

    # CSV 読み込み (デフォルト使用パス相当)
    with open(lp(csv_path), 'r', encoding='utf-8') as file:
        text = file.read()
    converted_text = convert_to_circumflex(text)
    csv_buffer = StringIO(converted_text)
    CSV_data_imported = pd.read_csv(csv_buffer, encoding='utf-8', usecols=[0, 1])

    # 語根分解法JSON / 置換後文字列JSON
    with open(lp(stemming_json_path), 'r', encoding='utf-8') as g:
        custom_stemming_setting_list = json.load(g)
    with open(lp(user_repl_json_path), 'r', encoding='utf-8') as g:
        user_replacement_item_setting_list = json.load(g)

    # ===== ボタンブロック (行360〜) =====
    with open(lp(estem_path), 'r', encoding='utf-8') as g:
        E_stem_with_Part_Of_Speech_list = json.load(g)

    temporary_replacements_dict = {}
    with open(lp(rootlist_path), 'r', encoding='utf-8') as file:
        for E_root in file.readlines():
            E_root = E_root.strip()
            if not E_root.isdigit():
                temporary_replacements_dict[E_root] = [E_root, len(E_root)]

    for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
        if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
            temporary_replacements_dict[E_root] = [output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict), len(E_root)]

    temporary_replacements_list_1 = []
    for old, new in temporary_replacements_dict.items():
        temporary_replacements_list_1.append((old, new[0], new[1]))
    temporary_replacements_list_2 = sorted(temporary_replacements_list_1, key=lambda x: x[2], reverse=True)

    temporary_replacements_list_final = []
    for kk in range(len(temporary_replacements_list_2)):
        temporary_replacements_list_final.append([temporary_replacements_list_2[kk][0], temporary_replacements_list_2[kk][1], imported_placeholders_for_global_replacement[kk]])

    # word_anno はスラッシュ除去形でも引けるようにする(E_stemと注釈版でスラッシュ位置が
    # 食い違う語のため。出力は後段でどのみち'/'除去されるので、注釈版の分解を採用して安全)。
    word_anno_nosl = None
    if word_anno is not None:
        word_anno_nosl = {}
        for _k, _v in word_anno.items():
            word_anno_nosl.setdefault(_k.replace('/', ''), _v)

    # per-word注釈からルビを構築(文脈依存訳; 無い語はper-root safe_replaceにフォールバック)
    def build_ruby_from_anno(pairs):
        segs = []
        for piece, trans in pairs:
            if trans and trans != piece and not _LATIN.match(trans):
                segs.append(output_format(piece, trans, format_type, char_widths_dict))
            else:
                segs.append(piece)
        return '/'.join(segs)

    def word_ruby_with_ending(i_x):
        """AN/ON等のスラッシュ分解(語尾付き)について、語幹がword_annoにあればper-word訳を採用。"""
        pieces = [p for p in i_x.split('/') if p]
        if len(pieces) >= 2 and word_anno_nosl is not None:
            stem_nosl = ''.join(pieces[:-1]); ending = pieces[-1]
            if stem_nosl in word_anno_nosl:
                return build_ruby_from_anno(word_anno_nosl[stem_nosl]) + '/' + ending
        return safe_replace(i_x, temporary_replacements_list_final)

    # pre_replacements_dict_1: E_stem を per-root置換。use_parallelで並列(Streamlit Cloud用)。
    if use_parallel:
        pre_replacements_dict_1 = parallel_build_pre_replacements_dict(
            E_stem_with_Part_Of_Speech_list, temporary_replacements_list_final, num_processes)
    else:
        pre_replacements_dict_1 = {}
        for i, j in enumerate(E_stem_with_Part_Of_Speech_list):
            if len(j) == 2 and len(j[0]) >= 2:
                if j[0] in pre_replacements_dict_1:
                    if j[1] not in pre_replacements_dict_1[j[0]][1]:
                        pre_replacements_dict_1[j[0]] = [pre_replacements_dict_1[j[0]][0], pre_replacements_dict_1[j[0]][1] + ',' + j[1]]
                else:
                    pre_replacements_dict_1[j[0]] = [safe_replace(j[0], temporary_replacements_list_final), j[1]]
    # word_anno(per-word文脈グロス)を後処理で上書き(serial/parallel共通。固有名詞の偽友グロス回避)。
    if word_anno_nosl is not None:
        for _k in pre_replacements_dict_1:
            _ns = _k.replace('/', '')
            if _ns in word_anno_nosl:
                pre_replacements_dict_1[_k][0] = build_ruby_from_anno(word_anno_nosl[_ns])

    for key in ['domen', 'teren', 'posten']:
        pre_replacements_dict_1.pop(key, None)

    pre_replacements_dict_2 = {}
    for i, j in pre_replacements_dict_1.items():
        if i == j[0]:
            pre_replacements_dict_2[i.replace('/', '')] = [j[0].replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), j[1], len(i.replace('/', '')) * 10000 - 3000]
        else:
            pre_replacements_dict_2[i.replace('/', '')] = [j[0].replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), j[1], len(i.replace('/', '')) * 10000]

    verb_suffix_2l_2 = {}
    for original_verb_suffix, replaced_verb_suffix in verb_suffix_2l.items():
        verb_suffix_2l_2[original_verb_suffix] = safe_replace(replaced_verb_suffix, temporary_replacements_list_final)

    unchangeable_after_creation_list = []
    AN_replacement = safe_replace('an', temporary_replacements_list_final)
    AN_treatment = []

    pre_replacements_dict_3 = {}
    pre_replacements_dict_2_copy = pre_replacements_dict_2.copy()
    for i, j in pre_replacements_dict_2_copy.items():
        if i.endswith('an') and (AN_replacement in j[0]) and ("名词" in j[1]) and (i[:-2] in pre_replacements_dict_2_copy):
            AN_treatment.append([i, j[0]])
            pre_replacements_dict_2.pop(i, None)
            for k in ["o", "a", "e"]:
                if not i + k in pre_replacements_dict_2_copy:
                    pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 2000]
        elif (j[1] == "名词") and (len(i) <= 6) and not (j[2] == 60000 or j[2] == 50000 or j[2] == 40000 or j[2] == 30000 or j[2] == 20000):
            for k in ["o"]:
                if not i + k in pre_replacements_dict_2_copy:
                    pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 2000]
                else:
                    pass
            pre_replacements_dict_2.pop(i, None)

    for i, j in pre_replacements_dict_2.items():
        if j[2] == 20000:
            if "名词" in j[1]:
                for k in ["o", "on", 'oj', 'ojn']:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pass
            if "形容词" in j[1]:
                for k in ["a", "aj", 'an', 'ajn']:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        unchangeable_after_creation_list.append(i + k)
            if "副词" in j[1]:
                for k in ["e"]:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
                    else:
                        pre_replacements_dict_3[' ' + i + k] = [' ' + j[0] + k, j[2] + (len(k) + 1) * 10000 - 5000]
            if "动词" in j[1]:
                for k1, k2 in verb_suffix_2l_2.items():
                    if not i + k1 in pre_replacements_dict_2:
                        pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                    elif j[0] + k2 != pre_replacements_dict_2[i + k1][0]:
                        pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                        unchangeable_after_creation_list.append(i + k1)
                for k in ["u ", "i ", "u", "i"]:
                    if not i + k in pre_replacements_dict_2:
                        pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                    elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                        pass
            continue
        else:
            if not i in unchangeable_after_creation_list:
                pre_replacements_dict_3[i] = [j[0], j[2]]
            if j[2] == 60000 or j[2] == 50000 or j[2] == 40000 or j[2] == 30000:
                if "名词" in j[1]:
                    for k in ["o", "on", 'oj', 'ojn']:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "形容词" in j[1]:
                    for k in ["a", "aj", 'an', 'ajn']:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
                if "动词" in j[1]:
                    for k1, k2 in verb_suffix_2l_2.items():
                        if not i + k1 in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                        elif j[0] + k2 != pre_replacements_dict_2[i + k1][0]:
                            pre_replacements_dict_3[i + k1] = [j[0] + k2, j[2] + len(k1) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k1)
                    for k in ["u ", "i ", "u", "i"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 3000]
                            unchangeable_after_creation_list.append(i + k)
            elif len(i) >= 3 and len(i) <= 6:
                if "名词" in j[1]:
                    for k in ["o"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass
                if "形容词" in j[1]:
                    for k in ["a"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass
                if "副词" in j[1]:
                    for k in ["e"]:
                        if not i + k in pre_replacements_dict_2:
                            pre_replacements_dict_3[i + k] = [j[0] + k, j[2] + len(k) * 10000 - 5000]
                        elif j[0] + k != pre_replacements_dict_2[i + k][0]:
                            pass

    for an in AN:
        if an[1].endswith("/an/"):
            i2 = an[1]; i3 = re.sub(r"/an/$", "", i2)
            for suf in ["/an/o", "/an/a", "/an/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/a/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), (len(i_x.replace('/', '')) - 1) * 10000 + 3000]
        else:
            i2 = an[1]; i2_2 = re.sub(r"an$", "", i2); i3 = re.sub(r"an/$", "", i2_2)
            for suf in ["an/o", "an/a", "an/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/a/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), (len(i_x.replace('/', '')) - 1) * 10000 + 3000]

    for on in ON:
        if on[1].endswith("/on/"):
            i2 = on[1]; i3 = re.sub(r"/on/$", "", i2)
            for suf in ["/on/o", "/on/a", "/on/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/o/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), (len(i_x.replace('/', '')) - 1) * 10000 + 3000]
        else:
            i2 = on[1]; i2_2 = re.sub(r"on$", "", i2); i3 = re.sub(r"on/$", "", i2_2)
            for suf in ["on/o", "on/a", "on/e", None]:
                i_x = (i3 + suf) if suf else (i3 + "/o/n/")
                pre_replacements_dict_3[i_x.replace('/', '')] = [word_ruby_with_ending(i_x).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>"), (len(i_x.replace('/', '')) - 1) * 10000 + 3000]

    # custom_stemming_setting_list
    if len(custom_stemming_setting_list) > 0:
        if len(custom_stemming_setting_list[0]) != 3:
            custom_stemming_setting_list.pop(0)
    for i in custom_stemming_setting_list:
        if len(i) == 3:
            try:
                esperanto_Word_before_replacement = i[0].replace('/', '')
                if i[1] == "dflt":
                    replacement_priority_by_length = len(esperanto_Word_before_replacement) * 10000
                elif i[1] in allowed_values:
                    pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                    if "ne" in i[2]:
                        pre_replacements_dict_3.pop(esperanto_Word_before_replacement, None)
                        i[2].remove("ne")
                    if "verbo_s1" in i[2]:
                        for k1 in verb_suffix_2l_2.keys():
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + k1, None)
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ", "i ", "u", "i"]:
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + k, None)
                        i[2].remove("verbo_s2")
                    if len(i[2]) >= 1:
                        for jj in i[2]:
                            j2 = jj.replace('/', '')
                            pre_replacements_dict_3.pop(esperanto_Word_before_replacement + j2, None)
                    continue
                elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                    replacement_priority_by_length = int(i[1])
                # 設定JSONの語幹: 注釈版(word_anno)が「語幹全体を1ユニットとして持つ」場合のみ採用
                # (固有名詞の偽友グロス回避。複数片に分節する語はsafe_replaceの語根単位グロスを優先し、
                #  word_annoの旧分節による上書き退行=alten→al/ten 等を防ぐ)
                _stem_ns = i[0].replace('/', '')
                _wa = word_anno_nosl.get(_stem_ns) if word_anno_nosl is not None else None
                if _wa is not None and len(_wa) == 1 and _wa[0][0].replace('/', '') == _stem_ns:
                    Replaced_String = build_ruby_from_anno(_wa).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                else:
                    Replaced_String = safe_replace(i[0], temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                if "ne" in i[2]:
                    pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
                    i[2].remove("ne")
                if "verbo_s1" in i[2]:
                    for k1, k2 in verb_suffix_2l_2.items():
                        pre_replacements_dict_3[esperanto_Word_before_replacement + k1] = [Replaced_String + k2, replacement_priority_by_length + len(k1) * 10000]
                    i[2].remove("verbo_s1")
                if "verbo_s2" in i[2]:
                    for k in ["u ", "i ", "u", "i"]:
                        pre_replacements_dict_3[esperanto_Word_before_replacement + k] = [Replaced_String + k, replacement_priority_by_length + len(k) * 10000]
                    i[2].remove("verbo_s2")
                if len(i[2]) >= 1:
                    for jj in i[2]:
                        j2 = jj.replace('/', '')
                        # 純粋な文法語尾(o/oj/on/ojn/a/aj/an/ajn/e/en/n/j等)はリテラル付加
                        # (通常名詞処理と整合。対格onが分数接尾辞-on-に誤マッチするのを防ぐ)
                        if j2 in _GRAM_ENDINGS:
                            j3 = j2
                        else:
                            j3 = safe_replace(jj, temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                        pre_replacements_dict_3[esperanto_Word_before_replacement + j2] = [Replaced_String + j3, replacement_priority_by_length + len(j2) * 10000]
                else:
                    pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
            except:
                continue

    # user_replacement_item_setting_list
    if len(user_replacement_item_setting_list) > 0:
        if len(user_replacement_item_setting_list[0]) != 4:
            user_replacement_item_setting_list.pop(0)
    for i in user_replacement_item_setting_list:
        if len(i) == 4:
            try:
                esperanto_Roots_before_replacement = i[0].strip('/').split('/')
                replaced_roots = i[3].strip('/').split('/')
                if len(esperanto_Roots_before_replacement) == len(replaced_roots):
                    Replaced_String = ""
                    for kk in range(len(esperanto_Roots_before_replacement)):
                        Replaced_String += output_format(esperanto_Roots_before_replacement[kk], replaced_roots[kk], format_type, char_widths_dict)
                    esperanto_Word_before_replacement = i[0].replace('/', '')
                    if i[1] == "dflt":
                        replacement_priority_by_length = len(esperanto_Word_before_replacement) * 10000
                    elif isinstance(i[1], int) or (isinstance(i[1], str) and i[1].isdigit()):
                        replacement_priority_by_length = int(i[1])
                    if "ne" in i[2]:
                        pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
                        i[2].remove("ne")
                    if "verbo_s1" in i[2]:
                        for k1, k2 in verb_suffix_2l_2.items():
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k1] = [Replaced_String + k2, replacement_priority_by_length + len(k1) * 10000]
                        i[2].remove("verbo_s1")
                    if "verbo_s2" in i[2]:
                        for k in ["u ", "i ", "u", "i"]:
                            pre_replacements_dict_3[esperanto_Word_before_replacement + k] = [Replaced_String + k, replacement_priority_by_length + len(k) * 10000]
                        i[2].remove("verbo_s2")
                    if len(i[2]) >= 1:
                        for jj in i[2]:
                            j2 = jj.replace('/', '')
                            j3 = safe_replace(jj, temporary_replacements_list_final).replace("</rt></ruby>", "%%%").replace('/', '').replace("%%%", "</rt></ruby>")
                            pre_replacements_dict_3[esperanto_Word_before_replacement + j2] = [Replaced_String + j3, replacement_priority_by_length + len(j2) * 10000]
                    else:
                        pre_replacements_dict_3[esperanto_Word_before_replacement] = [Replaced_String, replacement_priority_by_length]
            except:
                continue

    pre_replacements_list_1 = []
    for old, new in pre_replacements_dict_3.items():
        if isinstance(new[1], int):
            pre_replacements_list_1.append((old, new[0], new[1]))
    pre_replacements_list_2 = sorted(pre_replacements_list_1, key=lambda x: x[2], reverse=True)

    pre_replacements_list_3 = []
    for kk in range(len(pre_replacements_list_2)):
        if len(pre_replacements_list_2[kk][0]) >= 3:
            pre_replacements_list_3.append([pre_replacements_list_2[kk][0], remove_redundant_ruby_if_identical(pre_replacements_list_2[kk][1]), imported_placeholders_for_global_replacement[kk]])

    # 大文字化で rb(語根)の幅が変わる(例 v=8→V=10.7, ĉ=8→Ĉ=11.6)ため、大文字/先頭大文字
    # 変種はルビサイズ(rtのCSSクラス)を「実際のcased rb」で output_format により再計算する。
    # これをしないと、小文字語根の幅で決めたサイズを流用し、短語根で最大3段ずれる(要件7.4)。
    _RUBYFIX = re.compile(r'<ruby>([^<]+)<rt class="[^"]+">((?:[^<]|<br>)*)</rt></ruby>', re.IGNORECASE)
    def _resize_caps(h):
        return _RUBYFIX.sub(lambda mo: output_format(mo.group(1), mo.group(2).replace('<br>', ''), format_type, char_widths_dict), h)

    pre_replacements_list_4 = []
    if format_type in ('HTML格式_Ruby文字_大小调整', 'HTML格式_Ruby文字_大小调整_汉字替换', 'HTML格式', 'HTML格式_汉字替换'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            pre_replacements_list_4.append((old.upper(), _resize_caps(new.upper()), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                cap_old = old[0] + old[1:].capitalize(); cap_new = new[0] + capitalize_ruby_and_rt(new[1:])
            else:
                cap_old = old.capitalize(); cap_new = capitalize_ruby_and_rt(new)
            cap_new = _resize_caps(cap_new)
            pre_replacements_list_4.append((cap_old, cap_new, place_holder[:-1] + 'cap$'))
            # ハイフン複合の各部大文字変種(固有名詞 Abu-Dabi 等。実テキストはこの形)
            if '-' in old.strip().strip('-'):
                pc_old = _cap_after_hyphen(cap_old)
                if pc_old != cap_old:
                    pre_replacements_list_4.append((pc_old, _resize_caps(_cap_after_hyphen(cap_new)), place_holder[:-1] + 'pc$'))
    elif format_type in ('括弧(号)格式', '括弧(号)格式_汉字替换'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            pre_replacements_list_4.append((old.upper(), new.upper(), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                pre_replacements_list_4.append((old[0] + old[1:].capitalize(), new[0] + new[1:].capitalize(), place_holder[:-1] + 'cap$'))
            else:
                pre_replacements_list_4.append((old.capitalize(), new.capitalize(), place_holder[:-1] + 'cap$'))
    elif format_type in ('替换后文字列のみ(仅)保留(简单替换)'):
        for old, new, place_holder in pre_replacements_list_3:
            pre_replacements_list_4.append((old, new, place_holder))
            pre_replacements_list_4.append((old.upper(), new.upper(), place_holder[:-1] + 'up$'))
            if old[0] == ' ':
                pre_replacements_list_4.append((old[0] + old[1:].capitalize(), new[0] + new[1:].capitalize(), place_holder[:-1] + 'cap$'))
            else:
                pre_replacements_list_4.append((old.capitalize(), new.capitalize(), place_holder[:-1] + 'cap$'))

    replacements_final_list = []
    for old, new, place_holder in pre_replacements_list_4:
        modified_placeholder = place_holder
        if old.startswith(' '):
            modified_placeholder = ' ' + modified_placeholder
            if not new.startswith(' '):
                new = ' ' + new
        if old.endswith(' '):
            modified_placeholder = modified_placeholder + ' '
            if not new.endswith(' '):
                new = new + ' '
        replacements_final_list.append((old, new, modified_placeholder))

    replacements_list_for_suffix_2char_roots = []
    for i in range(len(suffix_2char_roots)):
        replaced_suffix = remove_redundant_ruby_if_identical(safe_replace(suffix_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i], "$" + replaced_suffix, "$" + imported_placeholders_for_2char_replacement[i]])
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i].upper(), "$" + _resize_caps(replaced_suffix.upper()), "$" + imported_placeholders_for_2char_replacement[i][:-1] + 'up$'])
        replacements_list_for_suffix_2char_roots.append(["$" + suffix_2char_roots[i].capitalize(), "$" + _resize_caps(capitalize_ruby_and_rt(replaced_suffix)), "$" + imported_placeholders_for_2char_replacement[i][:-1] + 'cap$'])

    replacements_list_for_prefix_2char_roots = []
    for i in range(len(prefix_2char_roots)):
        replaced_prefix = remove_redundant_ruby_if_identical(safe_replace(prefix_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i] + "$", replaced_prefix + "$", imported_placeholders_for_2char_replacement[i + 1000] + "$"])
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].upper() + "$", _resize_caps(replaced_prefix.upper()) + "$", imported_placeholders_for_2char_replacement[i + 1000][:-1] + 'up$' + "$"])
        replacements_list_for_prefix_2char_roots.append([prefix_2char_roots[i].capitalize() + "$", _resize_caps(capitalize_ruby_and_rt(replaced_prefix)) + "$", imported_placeholders_for_2char_replacement[i + 1000][:-1] + 'cap$' + "$"])

    replacements_list_for_standalone_2char_roots = []
    for i in range(len(standalone_2char_roots)):
        replaced_standalone = remove_redundant_ruby_if_identical(safe_replace(standalone_2char_roots[i], temporary_replacements_list_final))
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i] + " ", " " + replaced_standalone + " ", " " + imported_placeholders_for_2char_replacement[i + 2000] + " "])
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i].upper() + " ", " " + _resize_caps(replaced_standalone.upper()) + " ", " " + imported_placeholders_for_2char_replacement[i + 2000][:-1] + 'up$' + " "])
        replacements_list_for_standalone_2char_roots.append([" " + standalone_2char_roots[i].capitalize() + " ", " " + _resize_caps(capitalize_ruby_and_rt(replaced_standalone)) + " ", " " + imported_placeholders_for_2char_replacement[i + 2000][:-1] + 'cap$' + " "])

    replacements_list_for_2char = replacements_list_for_standalone_2char_roots + replacements_list_for_suffix_2char_roots + replacements_list_for_prefix_2char_roots

    pre_replacements_list_for_localized_string_1 = []
    for _, (E_root, hanzi_or_meaning) in CSV_data_imported.iterrows():
        if pd.notna(E_root) and pd.notna(hanzi_or_meaning) and '#' not in E_root and (E_root != '') and (hanzi_or_meaning != ''):
            if E_root == hanzi_or_meaning:
                pre_replacements_list_for_localized_string_1.append([E_root, hanzi_or_meaning, len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.upper(), hanzi_or_meaning.upper(), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.capitalize(), hanzi_or_meaning.capitalize(), len(E_root)])
            else:
                pre_replacements_list_for_localized_string_1.append([E_root, output_format(E_root, hanzi_or_meaning, format_type, char_widths_dict), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.upper(), output_format(E_root.upper(), hanzi_or_meaning.upper(), format_type, char_widths_dict), len(E_root)])
                pre_replacements_list_for_localized_string_1.append([E_root.capitalize(), output_format(E_root.capitalize(), hanzi_or_meaning.capitalize(), format_type, char_widths_dict), len(E_root)])
    pre_replacements_list_for_localized_string_2 = sorted(pre_replacements_list_for_localized_string_1, key=lambda x: x[2], reverse=True)
    replacements_list_for_localized_string = []
    for kk in range(len(pre_replacements_list_for_localized_string_2)):
        replacements_list_for_localized_string.append([pre_replacements_list_for_localized_string_2[kk][0], pre_replacements_list_for_localized_string_2[kk][1], imported_placeholders_for_local_replacement[kk]])

    combined_data = {}
    combined_data["全域替换用のリスト(列表)型配列(replacements_final_list)"] = replacements_final_list
    combined_data["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"] = replacements_list_for_2char
    combined_data["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"] = replacements_list_for_localized_string
    return combined_data
