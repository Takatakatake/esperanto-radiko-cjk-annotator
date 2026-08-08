# -*- coding: utf-8 -*-
"""多パターン目視確認スイート: セクション別デモ+ルビ/漢字対比ページ+3言語ルビページ。"""
import json, sys, os, importlib, re
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
APPS = {'JA':r"\Esperanto-Kanji-Ruby-JA", 'ZH':r"\Esperanto-Kanji-Ruby-ZH", 'KO':r"\Esperanto-Kanji-Ruby-KO"}

SECTIONS = [
 ("1. 基本文・挨拶（最頻語）",
"""Saluton, kara amiko! Mi amas vin.
Ĉu vi parolas Esperanton? Jes, mi lernas ĝin ekde la pasinta jaro.
La suno brilas kaj la birdoj kantas en la ĝardeno."""),
 ("2. 動詞語尾・時制（as/is/os/us・分詞）",
"""Mi legas, vi legis, li legos, ŝi legus se ŝi povus.
La leganta knabo, la legita libro, la legonta studento.
Ili estas skribantaj leterojn kaj faradis ekzercojn."""),
 ("3. 造語接辞（ig/iĝ/ad/ist/ebl/ec/ej/il/ar/an）",
"""La instruisto instruigas la lernantojn en la lernejo.
La akvo boliĝas kaj la manĝado komenciĝas.
La skribilo estas uzebla, kaj la boneco de la homaro estas videbla.
La urbanoj kaj la montaro estas belaj."""),
 ("4. 相関詞（9系統）",
"""Kiu venis? Tiu, kiu amas ĉiun. Neniu scias kial.
Kio estas tio? Ĉio estas ie, sed nenio estas ĉi tie.
Kiam vi venos? Tiam, kiam mi povos. Mi ĉiam pensas pri vi.
Kiel vi fartas? Tiel bone, kiel neniam antaŭe.
Kies libro estas ties? Ĉies opinio gravas."""),
 ("5. 同綴り異義語（文脈で判別）★今回の成果",
"""Mi ne venis, ĉar la ĉaro estis rompita.
Sub la blua ĉielo, ili ĉiel klopodis sukcesi.
La ŝipo atingis la kajon, kaj ni kantis kaj dancis.
La fero estas metalo, sed la ferio estas ripozo.
Li falis teren, kaj la tereno estis malmola.
La lama viro renkontis lamaon en la templo.
Dum la vero venkas, la vesto restas en la ŝranko."""),
 ("6. 偽分解・国際語（ルビ=荒く/漢字=深く）★二本立て",
"""Esperanto estas internacia lingvo.
La kuracisto donis antibiotikon al la paciento.
La aŭtomobilo veturis al la astronomia observejo kun teleskopo.
La ortografio kaj la meritokratio estas malfacilaj vortoj.
Mi aĉetis ĉokoladon kaj fotografis la pejzaĝon en Eŭropo."""),
 ("7. 借用語・固有名詞（[人名][地名]・素通し保持）",
"""La tokiponuloj spektas filmojn en Jutubo.
Gerda malaperis! Ili kaptis Elzan kaj Peĉjon.
Mi vizitis Davaon kaj Tokion dum la somero.
La koronaviruso kaŭzis pandemion en la mondo."""),
 ("8. 大文字・見出し（cap/ALL CAPS）★逆転バグ修正確認",
"""ESPERANTO ESTAS FACILA LINGVO.
La Dio De La Amo Kaj La Espero.
ANTAŬEN AL LA ESTONTECO!"""),
 ("9. 数詞・分数・対格・複数",
"""Du kaj tri estas kvin. Duono kaj triono kaj dekono.
Mi vidis hundojn, katojn kaj birdojn en la parkoj.
Ŝi aĉetis milfoje pli ol mi."""),
 ("10. 長い注釈の折返し（XXS/XXXS）",
"""La anestezio kaj la hidrokarbono estas sciencaj vortoj.
La komputilo kalkulas la kompleksajn ekvaciojn rapide."""),
]

dl = os.path.join(os.environ["USERPROFILE"], "Downloads", "エスペラント_目視スイート_20260703")
os.makedirs(dl, exist_ok=True)

def load_app(app, kind):
    APPDIR = ROOT + APPS[app]; DATA = APPDIR + r"\app_data"
    sys.path.insert(0, APPDIR)
    import esp_text_replacement_module as M; importlib.reload(M)
    jn = "置換リスト_漢字.json" if kind=='K' else "置換リスト_ルビ.json"
    cmb = json.load(open(DATA + "\\" + jn, encoding='utf-8'))
    return M, DATA, (
        cmb["全域替换用のリスト(列表)型配列(replacements_final_list)"],
        cmb["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
        cmb["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"])

def convert(M, DATA, lists, text, fmt):
    g,l,c = lists
    ps = M.import_placeholders(DATA + r"\placeholders_skip.txt")
    pl = M.import_placeholders(DATA + r"\placeholders_localcapture.txt")
    return M.orchestrate_comprehensive_esperanto_text_replacement(text, ps, l, pl, g, c, fmt)

def header(M, fmt, title):
    h = M.apply_ruby_html_header_and_footer("@@BODY@@", fmt)
    head, tail = h.split("@@BODY@@")
    # <p class=text-M_M>内にブロック要素を入れるとpが強制終了しline-height 2.0を失いガタつく。
    # → 包みのpを閉じ、各ブロックを自前の <p class="text-M_M"> とする(見出しはp外)。
    head = head.replace("</head>", "<style>h2{border-left:6px solid #4a90d9;padding-left:8px;margin:1.6em 0 0.4em;font-size:1.05em;background:#eef5fc;line-height:1.4} .mode{color:#888;font-size:0.8em;margin:0.2em 0;line-height:1.4}</style><title>"+title+"</title></head>")
    head = head + "</p>"          # 包みpを即閉じ
    tail = "<p class='text-M_M'>" + tail  # 末尾の</p>と対に
    return head, tail

# --- 1) 3言語ルビページ ---
FMT_R='HTML格式_Ruby文字_大小调整'; FMT_K='HTML格式_Ruby文字_大小调整_汉字替换'
for app in ('JA','ZH','KO'):
    M, DATA, lists = load_app(app,'R')
    head, tail = header(M, FMT_R, f"ルビ確認 {app}")
    body=[]
    for t, es in SECTIONS:
        body.append(f"<h2>{t}</h2><p class='text-M_M'>"+convert(M,DATA,lists,es,FMT_R).replace(chr(10),"<br>\n")+"</p>")
    open(os.path.join(dl,f"ルビ_{app}.html"),"w",encoding="utf-8").write(head+"\n".join(body)+tail)
    print(f"ルビ_{app}.html 生成")

# --- 2) 総合対比ページ(JAルビ vs 漢字化) ---
M, DATA, listsR = load_app('JA','R')
_,_, listsK = load_app('JA','K')
head, tail = header(M, FMT_R, "総合対比: ルビ×漢字化")
body=["<p style='color:#555'>各セクション: <b>上段=注釈ルビ版(学習優先・荒い分解)</b> / <b>下段=漢字化版(マスター準拠・深い偽分解)</b></p>"]
for t, es in SECTIONS:
    rb=convert(M,DATA,listsR,es,FMT_R).replace(chr(10),"<br>\n")
    kj=convert(M,DATA,listsK,es,FMT_K).replace(chr(10),"<br>\n")
    body.append(f"<h2>{t}</h2><div class='mode'>▼ 注釈ルビ版</div><p class='text-M_M'>{rb}</p>"
                f"<div class='mode'>▼ 漢字化版</div><p class='text-M_M'>{kj}</p>")
open(os.path.join(dl,"0_総合対比_ルビ×漢字化.html"),"w",encoding="utf-8").write(head+"\n".join(body)+tail)
print("0_総合対比 生成")
print("\n出力先:", dl)
