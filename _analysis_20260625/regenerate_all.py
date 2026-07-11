# -*- coding: utf-8 -*-
"""道B: 大JSON一括再生成 (正式ルート)

使い方:  python regenerate_all.py
  1. 確定リスト(out/confirmed_tier30.json)を分解設定へ適用し、3言語のルビJSONを再生成
  2. ルビ事後修正(fix_ruby_postregen: 偽の友グロス等)
  3. 漢字マスター正本との全面再同期(resync_kanji_master: CSV+word_kanji再構築)
  4. 3言語の漢字JSONを再生成
  5. 漢字39語パッチ(fix_kanji_2890: 旧安全網)
  6. 純粋置換版JSONの再導出(derive_pure_kanji)
  7. 6JSON異常スキャン
  8. .bak掃除(prune_baks: 肥大化防止)

外部マスターが必要な工程は環境変数で場所を指定できる(既定は作者環境):
  ESP_GOLD_PATH          … 学習者版マスター辞書(62k行)
  ESP_KANJI_MASTER_PATH  … 漢字割り当てマスター
"""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ([sys.executable, os.path.join(HERE, 'apply_confirmed_now.py'), '30', '--write'], {'SKIP_VERIFY': '1'}),
    ([sys.executable, os.path.join(HERE, 'fix_ruby_postregen.py')], {}),
    # 漢字は正本(エスペラント語根＿漢字割り当て＿20260630)から全面再同期してから統合する(第18R以降の正道)
    ([sys.executable, os.path.join(HERE, 'resync_kanji_master.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'apply_kanji_now.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'fix_kanji_2890.py'), '--apply'], {}),  # 旧安全網(resync後は実質no-op)
    # 純粋置換版(タグなし)はHTML漢字JSONから毎回再導出する(忘れると陳腐化する成果物)
    ([sys.executable, os.path.join(HERE, 'derive_pure_kanji.py')], {}),
    ([sys.executable, os.path.join(HERE, 'anomaly_scan.py')], {}),
    # 全工程合格後に .bak_* を掃除(放置すると3GB超に膨張。現行成果物はgit+SSDで三重保全済み)
    ([sys.executable, os.path.join(HERE, 'prune_baks.py')], {}),
]
for cmd, env_add in STEPS:
    env = dict(os.environ); env.update(env_add)
    print('>>>', ' '.join(os.path.basename(c) for c in cmd[1:2] + cmd[2:]))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print(f'!! 失敗: {cmd[1]}'); sys.exit(1)
print('=== 道B 一括再生成 完了 ===')
