@echo on
setlocal enabledelayedexpansion
pushd "%~dp0"

echo CWD=%CD%
where python
python -V
python -c "import sys; print(sys.executable)"

mkdir data\processed 2>nul

echo === fetch_espn ===
python -u src\fetch_espn.py || goto :err

echo === transform_data (build master) ===
python -u src\transform_data.py || goto :err

echo === copy_to_powerbi ===
python -u src\copy_to_powerbi.py || goto :err

echo === verify outputs ===
if exist "data\processed\espn_master.csv" (
  echo ✅ Found data\processed\espn_master.csv
) else (
  echo ❌ MISSING data\processed\espn_master.csv
  dir data\processed
  goto :err
)

echo ✅ DONE
popd
exit /b 0

:err
echo ❌ ERRORLEVEL=%ERRORLEVEL%
popd
exit /b %ERRORLEVEL%
