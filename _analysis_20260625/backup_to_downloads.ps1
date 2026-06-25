# エスペラント関連資料を Downloads に日付付きでバックアップ (.git/__pycache__ は除外)
# 再利用可: powershell -File backup_to_downloads.ps1
$ErrorActionPreference = 'Continue'
$date = Get-Date -Format 'yyyyMMdd'
$dest = Join-Path $env:USERPROFILE "Downloads\エスペラント_backup_$date"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$sources = @(
  @{ name='app_JP_日本語版';  path='d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool' },
  @{ name='app_ZH_中文版';    path='d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese' },
  @{ name='app_KO_한국어판';  path='d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean' },
  @{ name='語根分解辞書_WSL'; path='\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619' },
  @{ name='漢字割り当てリスト'; path='D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621' }
)

foreach ($s in $sources) {
  $tgt = Join-Path $dest $s.name
  Write-Output "==== $($s.name) -> $tgt ===="
  if (Test-Path -LiteralPath $s.path) {
    # /MIR ミラー, /XD 除外ディレクトリ, /R:1 /W:1 リトライ抑制, /NFL /NDL /NP ログ簡略, /MT マルチスレッド
    robocopy $s.path $tgt /MIR /XD .git __pycache__ node_modules .ipynb_checkpoints /XF *.lock '.~lock.*' /R:1 /W:1 /NFL /NDL /NP /MT:16 | Out-Null
    $code = $LASTEXITCODE
    $sz = (Get-ChildItem -LiteralPath $tgt -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    Write-Output ("  done (robocopy exit={0}) size={1:N1} MB" -f $code, ($sz/1MB))
  } else {
    Write-Output "  SKIP (not found): $($s.path)"
  }
}
Write-Output ""
Write-Output "バックアップ完了: $dest"
