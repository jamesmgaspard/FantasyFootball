@echo off
REM ============================================================
REM FantasyFootball — one-click weekly pipeline (Windows / OneDrive)
REM ------------------------------------------------------------
REM - Activates venv
REM - Runs ESPN fetch + rebuild exports
REM - Refreshes stable names for Power BI (symlink/hardlink/copy)
REM - Verifies outputs & writes health log
REM - Logs everything to %PROJ%\logs\pipeline_YYYYMMDD-HHMMSS.log
REM ============================================================

setlocal ENABLEDELAYEDEXPANSION

REM --- Canonical OneDrive project paths
set "PROJ=%OneDrive%\Projects\FantasyFootball"
set "PROCESSED=%PROJ%\data\processed"
set "LOGDIR=%PROJ%\logs"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%PROCESSED%" mkdir "%PROCESSED%"

REM --- Timestamp for logs (yyyyMMdd-HHmmss)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%i"
set "PIPELOG=%LOGDIR%\pipeline_%TS%.log"
set "HEALTH=%PROCESSED%\hybrid_health_pc_%TS%.log"

echo === RUN_START %TS% === > "%PIPELOG%"
echo Project  : %PROJ% >> "%PIPELOG%"
echo Processed: %PROCESSED% >> "%PIPELOG%"
echo Python   : >> "%PIPELOG%"

REM --- Activate venv
if exist "%PROJ%\.venv\Scripts\activate.bat" (
  call "%PROJ%\.venv\Scripts\activate.bat"  >> "%PIPELOG%" 2>&1
) else (
  echo [INFO] No venv found at .venv. Creating one... >> "%PIPELOG%"
  pushd "%PROJ%"
  python -m venv .venv                         >> "%PIPELOG%" 2>&1 || goto :err
  popd
  call "%PROJ%\.venv\Scripts\activate.bat"     >> "%PIPELOG%" 2>&1
)

REM --- Show python version to log
python -c "import sys;print(sys.version);print(sys.executable)" >> "%PIPELOG%" 2>&1

REM --- Optional: install requirements
if exist "%PROJ%\requirements.txt" (
  echo [pip] Installing requirements.txt >> "%PIPELOG%"
  python -m pip install --upgrade pip     >> "%PIPELOG%" 2>&1
  python -m pip install -r "%PROJ%\requirements.txt" >> "%PIPELOG%" 2>&1
) else (
  echo [pip] Installing core deps (no requirements.txt found) >> "%PIPELOG%"
  python -m pip install --upgrade pip     >> "%PIPELOG%" 2>&1
  python -m pip install python-dotenv pandas numpy requests pyarrow >> "%PIPELOG%" 2>&1
)

REM --- ESPN fetch
echo [STEP] fetch_espn.py >> "%PIPELOG%"
python "%PROJ%\src\fetch_espn.py"          >> "%PIPELOG%" 2>&1 || goto :err

REM --- Rebuild exports
echo [STEP] rebuild_support_exports.py >> "%PIPELOG%"
python "%PROJ%\src\rebuild_support_exports.py" >> "%PIPELOG%" 2>&1 || goto :err

REM --- Refresh stable names (Power BI always points to these)
REM Create a temp PowerShell script on the fly and run it
set "TMPPS=%TEMP%\stable_names_%TS%.ps1"
> "%TMPPS%" (
  echo param(^[string^]$Processed = "%PROCESSED%")
  echo Set-Location $Processed
  echo $Map = @{
  echo ^  "players_weekly.csv"  = "players_weekly_*.csv"
  echo ^  "team_weekly.csv"     = "team_weekly_*.csv"
  echo ^  "top_by_position.csv" = "top_by_position_*.csv"
  echo ^  "top_dst.csv"         = "top_dst_*.csv"
  echo }
  echo function Get-NewestByYear(^[string^]$Pattern^) {
  echo ^  $c = Get-ChildItem -File -Name $Pattern ^| Sort-Object -Descending
  echo ^  if (-not $c^) { return $null }
  echo ^  $c ^| ForEach-Object {
  echo ^    if ($_ -match '\d{4}') { ^[PSCustomObject^]@{Name=$_; Year=[int]$Matches[0]} } else { ^[PSCustomObject^]@{Name=$_; Year=0} }
  echo ^  } ^| Sort-Object Year, Name -Descending ^| Select-Object -First 1 ^| Select-Object -ExpandProperty Name
  echo }
  echo function New-StableFile(^[string^]$StableName,^[string^]$Pattern^) {
  echo ^  $target = Get-NewestByYear $Pattern
  echo ^  if (-not $target^) { Write-Warning "No match for $Pattern"; return }
  echo ^  $stablePath = Join-Path $PWD $StableName
  echo ^  if (Test-Path $stablePath^) { Remove-Item $stablePath -Force }
  echo ^  try {
  echo ^    New-Item -ItemType SymbolicLink -Path $stablePath -Target (Join-Path $PWD $target) -Force ^| Out-Null
  echo ^    Write-Host "✓ Symlink $StableName -> $target"; return
  echo ^  } catch {}
  echo ^  try {
  echo ^    New-Item -ItemType HardLink -Path $stablePath -Target (Join-Path $PWD $target) -Force ^| Out-Null
  echo ^    Write-Host "✓ Hardlink $StableName -> $target"; return
  echo ^  } catch {}
  echo ^  Copy-Item $target $stablePath -Force
  echo ^  Write-Host "✓ Copied $StableName (fallback) from $target"
  echo }
  echo $Map.GetEnumerator(^) ^| ForEach-Object { New-StableFile $_.Key $_.Value }
)

echo [STEP] stable names refresh >> "%PIPELOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPPS%"   >> "%PIPELOG%" 2>&1
del "%TMPPS%" 2^>NUL

REM --- Verify outputs (players + position + dst required; team optional)
set "MISSING=0"
for %%F in ("players_weekly.csv" "top_by_position.csv" "top_dst.csv") do (
  if not exist "%PROCESSED%\%%~F" (
    echo [ERROR] Missing "%PROCESSED%\%%~F" >> "%PIPELOG%"
    set "MISSING=1"
  )
)
if "!MISSING!"=="1" goto :err

REM --- Health log (success)
echo OK %DATE% %TIME%  league=6378544  season=2025  ^>^> PowerBI stable names good. > "%HEALTH%"
echo [OK] Health log: %HEALTH% >> "%PIPELOG%"

echo === RUN_DONE %TS% === >> "%PIPELOG%"
echo ✅ DONE
exit /b 0

:err
echo === RUN_FAIL %TS% === >> "%PIPELOG%"
echo ❌ ERRORLEVEL=%ERRORLEVEL% >> "%PIPELOG%"
echo See log: %PIPELOG%
exit /b %ERRORLEVEL%