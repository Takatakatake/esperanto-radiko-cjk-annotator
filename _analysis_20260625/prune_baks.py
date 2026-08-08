# -*- coding: utf-8 -*-
"""再生成スクリプト群が作る .bak_* を掃除する(異常スキャン合格後に実行される前提)。
   現行成果物はgit+SSDに三重保全されており、.bakは一時安全網にすぎない。
   放置すると3アプリで3GB超に膨らむ(2026-07-07に実測)ため、パイプライン末尾で自動掃除する。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFX = chr(92) + chr(92) + chr(63) + chr(92)
freed = 0; n = 0
for sub in ('Esperanto-Kanji-Ruby-JA', 'Esperanto-Kanji-Ruby-ZH', 'Esperanto-Kanji-Ruby-KO', '_analysis_20260625'):
    root = PFX + os.path.abspath(os.path.join(BASE, sub))
    for r, _, fs in os.walk(root):
        if os.sep + '.git' in r: continue
        for f in fs:
            if '.bak' in f or f.endswith('.backup'):
                p = os.path.join(r, f)
                try:
                    s = os.path.getsize(p); os.remove(p); freed += s; n += 1
                except OSError: pass
print(f".bak掃除: {n}個 / {freed/1048576:.0f}MB 解放")
