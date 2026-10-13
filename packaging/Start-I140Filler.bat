@echo off
setlocal
cd /d "%~dp0"

echo Starting I140Filler...
echo Folder: %CD%
echo.

if not exist "I140Filler.exe" (
  echo ERROR: I140Filler.exe not found in this folder.
  echo Extract the FULL zip first. Do not run from inside the .zip.
  goto :end
)

if not exist "_internal\gradio_client\types.json" (
  echo ERROR: Missing _internal\gradio_client\types.json
  echo The zip extract is incomplete. Delete this folder and unzip again.
  goto :end
)

echo Launching... first start can take 30-60 seconds.
echo If a browser does not open, go to http://127.0.0.1:7860
echo.
I140Filler.exe
set ERR=%ERRORLEVEL%
echo.
echo Exit code: %ERR%
if not "%ERR%"=="0" (
  echo.
  echo The app exited with an error. Copy the text above and send it for support.
)

:end
echo.
pause
endlocal
