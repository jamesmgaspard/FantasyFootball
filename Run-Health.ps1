$Project = "C:\Users\JMiniPC\OneDrive\Projects\FantasyFootball"
$LogDir  = Join-Path $Project "data\processed"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$Log   = Join-Path $LogDir "hybrid_health_pc_$Stamp.log"

"Running PC Hybrid Health @ $Stamp" | Tee-Object -FilePath $Log
& (Join-Path $Project "HybridHealth.ps1") $args 2>&1 | Tee-Object -FilePath $Log -Append
$code = $LASTEXITCODE
"--- Exit code: $code ---" | Tee-Object -FilePath $Log -Append
exit $code
