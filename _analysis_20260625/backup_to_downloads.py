# -*- coding: utf-8 -*-
"""
エスペラント関連資料を Downloads に日付付きでバックアップ (.git/__pycache__ 等は除外)。
robocopy をミラーモードで使用。再利用可: python backup_to_downloads.py
"""
import os, subprocess, datetime, sys
sys.stdout.reconfigure(encoding="utf-8")

date = datetime.date.today().strftime("%Y%m%d")
dest_root = os.path.join(os.environ["USERPROFILE"], "Downloads", f"エスペラント_backup_{date}")
os.makedirs(dest_root, exist_ok=True)

BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sources = [
    ("app_JP_日本語版",   BASE + r"\Esperanto-Kanji-Ruby-JA"),
    ("app_ZH_中文版",     BASE + r"\Esperanto-Kanji-Ruby-ZH"),
    ("app_KO_韓国語版",   BASE + r"\Esperanto-Kanji-Ruby-KO"),
    ("語根分解辞書_WSL",  r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619"),
    ("漢字割り当てリスト", r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621"),
]

def folder_size_mb(p):
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total / (1024*1024)

for name, path in sources:
    tgt = os.path.join(dest_root, name)
    print(f"==== {name} ====")
    if not os.path.exists(path):
        print(f"  SKIP (not found): {path}")
        continue
    # robocopy /MIR ミラー, /XD 除外, /R:1 /W:1, /NFL /NDL /NP /NJH /NJS 静音, /MT:16
    cmd = ["robocopy", path, tgt, "/MIR",
           "/XD", ".git", "__pycache__", "node_modules", ".ipynb_checkpoints",
           "/XF", "*.lock",
           "/R:1", "/W:1", "/NFL", "/NDL", "/NP", "/NJH", "/NJS", "/MT:16"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # robocopy: 0-7 は成功系, 8+ は失敗
    code = res.returncode
    status = "OK" if code < 8 else "ERROR"
    print(f"  robocopy exit={code} ({status})  size={folder_size_mb(tgt):.1f} MB")
    if code >= 8:
        print("  STDERR:", (res.stderr or "")[:500])

print(f"\nバックアップ完了: {dest_root}")
