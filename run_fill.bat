@echo off
setlocal
cd /d "%~dp0"
python fill_i140.py --word "%~1" --output "%~2"
if "%~2"=="" (
  python fill_i140.py --word "%~1"
)
endlocal
