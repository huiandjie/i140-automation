@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo === I-140 Filler distribution build ===
echo Strategy:
echo   1^) Nuitka-compile core logic to .pyd ^(protects source^)
echo   2^) PyInstaller packages Gradio UI into a folder you can zip
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found on PATH.
  exit /b 1
)

python -m pip install -q -U nuitka ordered-set zstandard pyinstaller

if not exist "assets\i-140-uscis.pdf" (
  if exist "test\i-140-uscis.pdf" (
    mkdir assets 2>nul
    copy /Y "test\i-140-uscis.pdf" "assets\i-140-uscis.pdf" >nul
  ) else (
    echo ERROR: Missing assets\i-140-uscis.pdf
    exit /b 1
  )
)

REM Resolve site-packages paths for explicit Gradio data files
for /f "delims=" %%i in ('python -c "import gradio_client,pathlib;print(pathlib.Path(gradio_client.__file__).parent)"') do set "GC_DIR=%%i"
for /f "delims=" %%i in ('python -c "import gradio,pathlib;print(pathlib.Path(gradio.__file__).parent)"') do set "G_DIR=%%i"
if not exist "%GC_DIR%\types.json" (
  echo ERROR: gradio_client types.json not found at %GC_DIR%
  exit /b 1
)

set "BUILD_LIBS=build\libs"
if exist "%BUILD_LIBS%" rmdir /S /Q "%BUILD_LIBS%"
mkdir "%BUILD_LIBS%" 2>nul
mkdir build 2>nul

echo.
echo [1/3] Compiling core modules with Nuitka...
python -m nuitka --module models.py --output-dir="%BUILD_LIBS%" --remove-output --assume-yes-for-downloads
if errorlevel 1 goto :fail
python -m nuitka --module pdf_filler.py --include-module=models --output-dir="%BUILD_LIBS%" --remove-output --assume-yes-for-downloads
if errorlevel 1 goto :fail
python -m nuitka --module word_extractor.py --include-module=models --output-dir="%BUILD_LIBS%" --remove-output --assume-yes-for-downloads
if errorlevel 1 goto :fail

echo.
echo [2/3] Packaging UI with PyInstaller...
REM Hide .py sources so the frozen app loads compiled .pyd instead
if not exist "build\src_backup" mkdir "build\src_backup"
move /Y models.py build\src_backup\ >nul
move /Y pdf_filler.py build\src_backup\ >nul
move /Y word_extractor.py build\src_backup\ >nul
copy /Y "%BUILD_LIBS%\*.pyd" . >nul
copy /Y "%BUILD_LIBS%\*.pyi" . >nul 2>nul

if exist "dist\I140Filler" rmdir /S /Q "dist\I140Filler"
if exist "build\pyinstaller" rmdir /S /Q "build\pyinstaller"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --name I140Filler ^
  --distpath dist ^
  --workpath build\pyinstaller ^
  --noupx ^
  --add-data "assets\i-140-uscis.pdf;assets" ^
  --add-data "%GC_DIR%\types.json;gradio_client" ^
  --add-data "%GC_DIR%\package.json;gradio_client" ^
  --add-binary "*.pyd;." ^
  --copy-metadata gradio ^
  --copy-metadata gradio_client ^
  --copy-metadata safehttpx ^
  --copy-metadata groovy ^
  --hidden-import=models ^
  --hidden-import=pdf_filler ^
  --hidden-import=word_extractor ^
  --hidden-import=win32com ^
  --hidden-import=win32com.client ^
  --hidden-import=pythoncom ^
  --hidden-import=pywintypes ^
  --hidden-import=pypdf ^
  --collect-all gradio ^
  --collect-all gradio_client ^
  --collect-all safehttpx ^
  --collect-all groovy ^
  --console ^
  app.py
set "PYI_ERR=%ERRORLEVEL%"

REM Always restore sources
move /Y build\src_backup\models.py . >nul
move /Y build\src_backup\pdf_filler.py . >nul
move /Y build\src_backup\word_extractor.py . >nul
del /Q *.pyd 2>nul
del /Q models.pyi pdf_filler.pyi word_extractor.pyi 2>nul

if not "%PYI_ERR%"=="0" goto :fail

echo.
echo [3/3] Finalizing package...
if not exist "dist\I140Filler\assets" mkdir "dist\I140Filler\assets"
copy /Y "assets\i-140-uscis.pdf" "dist\I140Filler\assets\i-140-uscis.pdf" >nul
if not exist "dist\I140Filler\output" mkdir "dist\I140Filler\output"
copy /Y "packaging\README_FOR_USERS.txt" "dist\I140Filler\README.txt" >nul
copy /Y "%BUILD_LIBS%\*.pyd" "dist\I140Filler\" >nul
if exist "dist\I140Filler\_internal" copy /Y "%BUILD_LIBS%\*.pyd" "dist\I140Filler\_internal\" >nul

REM Force-copy critical Gradio client data next to the package modules
if not exist "dist\I140Filler\_internal\gradio_client" mkdir "dist\I140Filler\_internal\gradio_client"
copy /Y "%GC_DIR%\types.json" "dist\I140Filler\_internal\gradio_client\types.json" >nul
copy /Y "%GC_DIR%\package.json" "dist\I140Filler\_internal\gradio_client\package.json" >nul
xcopy /E /I /Y "%GC_DIR%\templates" "dist\I140Filler\_internal\gradio_client\templates\" >nul

if not exist "dist\I140Filler\_internal\gradio_client\types.json" (
  echo ERROR: types.json missing from package after finalize
  goto :fail
)

echo.
echo Verifying launch import path...
python -c "from pathlib import Path; p=Path(r'dist/I140Filler/_internal/gradio_client/types.json'); assert p.is_file() and p.stat().st_size>0, p; print('OK', p, p.stat().st_size)"

echo.
echo Creating dist\I140Filler.zip ...
if exist "dist\I140Filler.zip" del /F /Q "dist\I140Filler.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\I140Filler' -DestinationPath 'dist\I140Filler.zip' -Force"

echo.
echo === Build complete ===
echo Folder: %CD%\dist\I140Filler
echo Zip:    %CD%\dist\I140Filler.zip
echo.
echo IMPORTANT: Delete any old extracted copy first, then unzip fresh.
echo Users run I140Filler.exe ^(requires Microsoft Word^).
exit /b 0

:fail
echo.
echo Restoring source files if needed...
if exist "build\src_backup\models.py" move /Y build\src_backup\models.py . >nul
if exist "build\src_backup\pdf_filler.py" move /Y build\src_backup\pdf_filler.py . >nul
if exist "build\src_backup\word_extractor.py" move /Y build\src_backup\word_extractor.py . >nul
del /Q models*.pyd pdf_filler*.pyd word_extractor*.pyd 2>nul
echo BUILD FAILED
exit /b 1
