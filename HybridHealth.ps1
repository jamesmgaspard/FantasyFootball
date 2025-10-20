param([string]$PipelineFlag = "")

# ===== CONFIG =====
$Project   = "C:\Users\JMiniPC\OneDrive\Projects\FantasyFootball"
$SyncDir   = Join-Path $Project "data\processed"
$SyncMac   = Join-Path $SyncDir "_sync_test_mac.txt"
$SyncPC    = Join-Path $SyncDir "_sync_test_pc.txt"
$VenvPy    = Join-Path $Project ".venv\Scripts\python.exe"
$SrcDir    = Join-Path $Project "src"
$FetchPy   = Join-Path $SrcDir "fetch_nflverse.py"
$RebuildPy = Join-Path $SrcDir "rebuild_support_exports.py"

# Data files we expect after a successful fetch/rebuild
$ExpectCsv = @(
  "players_weekly.csv",        # your unified weekly file
  "player_weekly.csv",         # alt name some pipelines produce
  "espn_player_weekly.csv",
  "weekly_stats.csv"           # fallback if you keep a combined weekly
) | ForEach-Object { Join-Path $SyncDir $_ }

# Treat files older than this as stale and trigger a refresh
$StaleDays = 7

# ===== UTIL =====
function Banner([string]$t){ Write-Host ""; Write-Host ("===== " + $t + " =====") }
function OK([string]$t){ Write-Host ("[OK]   " + $t) -ForegroundColor Green }
function WARN([string]$t){ Write-Host ("[WARN] " + $t) -ForegroundColor Yellow }
function FAIL([string]$t){ Write-Host ("[FAIL] " + $t) -ForegroundColor Red; throw ("FAIL: " + $t) }

function Ensure-Dir([string]$p){
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

function Ensure-Python([ref]$pyOut){
  if (Test-Path $VenvPy) {
    $pyOut.Value = $VenvPy
    OK ("Using venv python: " + $pyOut.Value)
  } else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $pyOut.Value = $cmd.Source }
    if (-not $pyOut.Value) { FAIL "No python found" }
    WARN ("No project venv detected; using system python: " + $pyOut.Value)
  }
  & $pyOut.Value --version | Out-Host
}

function Ensure-PyPkg($pyExe, $pkg){
  # return $true if package importable, otherwise install then recheck
  & $pyExe -c ("import " + $pkg) 2>$null
  if ($LASTEXITCODE -eq 0) { return $true }
  WARN ("Missing python package: " + $pkg + " -> installing")
  & $pyExe -m pip install --quiet --disable-pip-version-check $pkg
  & $pyExe -c ("import " + $pkg) 2>$null
  if ($LASTEXITCODE -ne 0) { FAIL ("Could not import python package after install: " + $pkg) }
  OK ("Installed package: " + $pkg)
  return $true
}

function Needs-FetchOrRebuild{
  # true if any expected CSV missing or all are older than $StaleDays
  $existing = $ExpectCsv | Where-Object { Test-Path $_ }
  if ($existing.Count -eq 0) { return $true }
  $cutoff = (Get-Date).AddDays(-$StaleDays)
  $allOld = $true
  foreach($f in $existing){
    $lt = (Get-Item $f).LastWriteTime
    if ($lt -gt $cutoff) { $allOld = $false }
  }
  return $allOld
}

function Run-Py($pyExe, $scriptPath){
  if (-not (Test-Path $scriptPath)) { WARN ("Missing script: " + $scriptPath); return $false }
  & $pyExe $scriptPath
  if ($LASTEXITCODE -ne 0) { WARN ("Script exit code " + $LASTEXITCODE + ": " + $scriptPath); return $false }
  return $true
}

# ===== BASIC SANITY =====
Banner "PC <-> OneDrive sanity"
Ensure-Dir $Project
Ensure-Dir $SyncDir
OK "Found project and data folders"

# ===== SYNC PULSE =====
Banner "Sync pulse"
("Sync check from PC on " + (Get-Date)) | Out-File -FilePath $SyncPC -Encoding UTF8
Start-Sleep -Seconds 1
if (Test-Path $SyncPC) { OK ("Updated " + $SyncPC) } else { FAIL ("Failed to update " + $SyncPC) }
if (Test-Path $SyncMac) { OK ("Detected " + $SyncMac) } else { WARN ("Mac file not found yet: " + $SyncMac) }

# Show pulse files
Get-ChildItem (Join-Path $SyncDir "_sync_test_*.txt") -ErrorAction SilentlyContinue |
  Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize

# ===== GIT HEALTH =====
Banner "Git health"
Set-Location $Project
if (-not (Test-Path ".git")) { FAIL ("Not a Git repo at " + $Project) }
git fetch --prune | Out-Null
OK "Fetched latest from origin"
$branch     = (git rev-parse --abbrev-ref HEAD).Trim()
$headHash   = (git rev-parse HEAD).Trim()
$originHash = (git rev-parse ("origin/" + $branch)).Trim()
Write-Host ("Current branch: " + $branch)
Write-Host ("HEAD: " + $headHash)
Write-Host ("origin/" + $branch + ": " + $originHash)
if ($headHash -eq $originHash) { OK ("Local == origin/" + $branch) } else { WARN ("Local != origin/" + $branch + " (consider: git pull)") }

# ===== PYTHON / VENV =====
Banner "Python env"
$py = $null
Ensure-Python ([ref]$py)

# Ensure critical packages (add more here if needed)
Ensure-PyPkg $py "nfl_data_py"   | Out-Null
Ensure-PyPkg $py "pandas"        | Out-Null
Ensure-PyPkg $py "fastparquet"   | Out-Null

# ===== FOLDER INTEGRITY =====
Banner "Folder integrity"
$dirs = @('data\raw','data\interim','data\processed','src','powerbi\inputs','powerbi\pbip','.vscode')
foreach($d in $dirs){
  $p = Join-Path $Project $d
  if (Test-Path $p) { OK ("Exists: " + $d) } else { WARN ("Missing: " + $d) }
}

# ===== SELF-HEAL: FETCH/REBUILD WHEN NEEDED =====
$didWork = $false
if (Needs-FetchOrRebuild) {
  Banner "Data refresh (self-heal)"
  # Try fetch first (ok if parts 404)
  if (Run-Py $py $FetchPy) { OK "Fetch completed" } else { WARN "Fetch had warnings/errors (continuing)" }
  # Then rebuild exports
  if (Run-Py $py $RebuildPy) { OK "Rebuild completed"; $didWork = $true } else { WARN "Rebuild reported non-zero exit" }
} else {
  WARN ("Weekly CSVs present and fresh (< " + $StaleDays + " days) â€” skip auto-refresh")
}

# ===== OPTIONAL PIPELINE FLAG (manual force) =====
if ($PipelineFlag -eq "--pipeline") {
  Banner "Forced pipeline (--pipeline)"
  if (Run-Py $py $RebuildPy) { OK "Forced rebuild completed" } else { WARN "Forced rebuild non-zero exit" }
}

# ===== POWER BI LINKAGE REMINDER =====
Banner "Power BI linkage (info)"
Write-Host "â€¢ In PBIX/PBIP, verify sources use:"
Write-Host "  C:\Users\JMiniPC\OneDrive\Projects\FantasyFootball\data\processed\..."
Write-Host "â€¢ Then Home -> Refresh All. Confirm 2025 on '01 â€“ Top 10 â€¢ PPR Avg (All)'."

# ===== BEACON (JSON) =====
try {
  $Beacon = @{
    host      = "PC"
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    branch    = $branch
    commit    = $headHash
    refreshed = $didWork
  }
  ($Beacon | ConvertTo-Json -Depth 3) | Set-Content -Path (Join-Path $SyncDir "pc_status.json") -Encoding UTF8
  OK "Wrote pc_status.json"
} catch {
  WARN ("Could not write pc_status.json: " + $_.Exception.Message)
}

# ===== CLEAN EXIT =====
OK "Windows Hybrid Health complete"
$global:LASTEXITCODE = 0
exit 0
