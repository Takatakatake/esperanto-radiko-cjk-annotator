# -*- coding: utf-8 -*-
"""道B: 大JSON一括再生成 (正式ルート)

使い方:  python regenerate_all.py
  1. 固定コーパスexact manifestが指定repoのclean HEADと一致するか検証
  2. 汎用規則適用後のreviewed evaluable exact manifestを同様に検証
  3. コーパス確定固有語注釈をword_anno日中韓へ同期
  4. 確定リスト(out/confirmed_tier30.json)を分解設定へ適用し、3言語のルビJSONを再生成
  5. ルビ事後修正(fix_ruby_postregen: 偽の友グロス等)
  6. 21,443 canonical表記を配置済み日中韓runtimeで全数検査
  7. 漢字マスター正本との全面再同期(resync_kanji_master: CSV+word_kanji再構築)
  8. 3言語の漢字JSONを再生成
  9. 漢字39語パッチ(fix_kanji_2890: 旧安全網)
 10. 純粋置換版JSONの再導出(derive_pure_kanji)
 11. 6JSON異常スキャン
 12. 生成規則+実機回帰テスト
 13. 日中韓Ruby全域構造一致検査
 14. .bak掃除(prune_baks: 肥大化防止)

外部マスターが必要な工程は環境変数で場所を指定できる(既定は作者環境):
  ESP_GOLD_PATH          … 学習者版マスター辞書(62k行)
  ESP_KANJI_MASTER_PATH  … 漢字割り当てマスター
  ESP_CORPUS_PATH        … 固定exact manifestの元になったcleanな京大HTML repo
"""
import hashlib, json, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_snapshot import consistent_snapshot

# No write starts until all external moving inputs are explicitly pinned.
# The reviewed scope manifest is the authority for the accepted gold identity;
# an asynchronously synchronized newer master must be audited separately before
# it can replace this snapshot.
for required in ("ESP_GOLD_PATH", "ESP_CORPUS_PATH", "ESP_KANJI_MASTER_PATH"):
    if not os.environ.get(required):
        raise SystemExit(f"formal regeneration requires explicit {required}")
with open(os.path.join(HERE, "_no_worsening_scope_manifest.json"), encoding="utf-8") as handle:
    scope_manifest = json.load(handle)
expected_gold = scope_manifest["expected"]["gold"]
_gold_raw, gold_identity = consistent_snapshot(os.environ["ESP_GOLD_PATH"])
if (
    gold_identity["sha256"] != expected_gold["sha256"]
    or gold_identity["bytes"] != expected_gold["bytes"]
):
    raise SystemExit(
        "pinned gold mismatch before regeneration: "
        f"expected {expected_gold['bytes']} bytes/{expected_gold['sha256']}, "
        f"got {gold_identity['bytes']} bytes/{gold_identity['sha256']}"
    )
COMMON_ENV = {"ESP_EXPECTED_GOLD_SHA256": expected_gold["sha256"]}
kanji_manifest_path = os.path.join(HERE, "_kanji_master_scope_manifest.json")
with open(kanji_manifest_path, encoding="utf-8") as handle:
    kanji_manifest = json.load(handle)
if kanji_manifest.get("schema_version") != 1:
    raise SystemExit("unsupported Kanji master manifest schema")
for expected in kanji_manifest["files"]:
    path = os.path.join(os.environ["ESP_KANJI_MASTER_PATH"], expected["name"])
    raw = open(path, "rb").read()
    actual_sha = hashlib.sha256(raw).hexdigest().upper()
    if len(raw) != expected["bytes"] or actual_sha != expected["sha256"]:
        raise SystemExit(
            f"pinned Kanji master mismatch: {expected['name']}: expected "
            f"{expected['bytes']} bytes/{expected['sha256']}, got "
            f"{len(raw)} bytes/{actual_sha}"
        )
COMMON_ENV["ESP_EXPECTED_KANJI_MASTER_MANIFEST"] = kanji_manifest_path
_kanji_injection = next(
    row for row in kanji_manifest["files"]
    if row["name"] == "漢字注入_学習者版_20260620.txt"
)
if sum(
    row.get("name") == _kanji_injection["name"]
    for row in kanji_manifest["files"]
) != 1:
    raise SystemExit("Kanji master manifest must pin exactly one injection file")
COMMON_ENV["ESP_EXPECTED_KANJI_MASTER_SHA256"] = _kanji_injection["sha256"]
STEPS = [
    ([sys.executable, os.path.join(HERE, 'build_corpus_exact_manifest.py'), '--check'], {}),
    ([sys.executable, os.path.join(HERE, 'build_corpus_reviewed_exact_manifest.py'), '--check'], {}),
    ([sys.executable, os.path.join(HERE, 'bare_word_audit.py'), '--require-zero'], {}),
    ([sys.executable, os.path.join(HERE, 'apply_corpus_word_anno.py'), '--write'], {}),
    # 3言語とも同一の固定正本 + 確定補正になることを、生成前にfail-closedで検査する。
    ([sys.executable, os.path.join(HERE, 'apply_confirmed_now.py'), '30', '--settings-audit'], {'SKIP_VERIFY': '1'}),
    ([sys.executable, os.path.join(HERE, 'apply_confirmed_now.py'), '30', '--write'], {'SKIP_VERIFY': '1'}),
    ([sys.executable, os.path.join(HERE, 'fix_ruby_postregen.py')], {}),
    # 全21443 canonical表記を配置済み3言語runtimeで描画し、残差0を漢字工程前に強制する。
    ([sys.executable, os.path.join(HERE, 'test_canonical_corpus_surfaces.py')], {}),
    ([sys.executable, os.path.join(HERE, 'check_canonical_corpus_surfaces.py')], {}),
    # 漢字は正本(エスペラント語根＿漢字割り当て＿20260630)から全面再同期してから統合する(第18R以降の正道)
    ([sys.executable, os.path.join(HERE, 'resync_kanji_master.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'apply_kanji_now.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'fix_kanji_2890.py'), '--apply'], {}),  # 旧安全網(resync後は実質no-op)
    # 純粋置換版(タグなし)はHTML漢字JSONから毎回再導出する(忘れると陳腐化する成果物)
    ([sys.executable, os.path.join(HERE, 'derive_pure_kanji.py')], {}),
    ([sys.executable, os.path.join(HERE, 'anomaly_scan.py')], {}),
    # 生成規則の単体テスト + 3言語デプロイJSONの実機回帰テスト。
    ([sys.executable, os.path.join(HERE, 'test_generation_regressions.py')], {}),
    ([sys.executable, os.path.join(HERE, 'test_reviewed_exact_manifest.py')], {}),
    ([sys.executable, os.path.join(HERE, 'check_multilingual_structure.py')], {}),
    ([sys.executable, os.path.join(HERE, 'check_raw_apostrophe_structure.py')], {}),
    # 全工程合格後に .bak_* を掃除(放置すると3GB超に膨張。現行成果物はgit+SSDで三重保全済み)
    ([sys.executable, os.path.join(HERE, 'prune_baks.py')], {}),
]
for cmd, env_add in STEPS:
    env = dict(os.environ); env.update(COMMON_ENV); env.update(env_add)
    print('>>>', ' '.join(os.path.basename(c) for c in cmd[1:2] + cmd[2:]))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        print(f'!! 失敗: {cmd[1]}'); sys.exit(1)
print('=== 道B 一括再生成 完了 ===')
