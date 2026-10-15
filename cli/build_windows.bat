@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo    Compilador de Kognito Sync para Windows (.exe)
echo ========================================================

REM 1. Verificar Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python no esta instalado o no se encuentra en el PATH.
    pause
    exit /b 1
)

REM 2. Directorio base
cd /d "%~dp0"

REM 3. Crear entorno virtual si no existe
if not exist "venv_build" (
    echo [*] Creando entorno virtual venv_build...
    python -m venv venv_build
)

call venv_build\Scripts\activate.bat

REM 4. Instalar dependencias necesarias
echo [*] Instalando y actualizando dependencias de compilacion...
python -m pip install --upgrade pip
pip install customtkinter pystray watchdog httpx pillow pyinstaller

REM 5. Generar iconos si no existen
if not exist "icon.ico" (
    echo [*] Generando icon.ico e icon.png...
    python generate_icons.py
)

REM 6. Compilar con PyInstaller
echo [*] Ejecutando PyInstaller...
pyinstaller --clean -y kognitosync.spec

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo la compilacion con PyInstaller.
    pause
    exit /b 1
)

echo [OK] Binario generado exitosamente en: dist\KognitoSync\KognitoSync.exe

REM 7. Buscar Inno Setup Compiler (ISCC.exe)
set "ISCC_PATH="
where iscc >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "ISCC_PATH=iscc"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
)

if defined ISCC_PATH (
    echo [*] Generando instalador con Inno Setup (!ISCC_PATH!)...
    "!ISCC_PATH!" installer.iss
    if !ERRORLEVEL! equ 0 (
        echo ========================================================
        echo  [EXITO] INSTALADOR CREADO SATISFACTORIAMENTE:
        echo  cli\dist-installer\KognitoSync-Setup.exe
        echo ========================================================
    ) else (
        echo [ERROR] Ocurrio un error al empaquetar con Inno Setup.
    )
) else (
    echo.
    echo [AVISO] Inno Setup no esta instalado o no se encontro ISCC.exe en el sistema.
    echo Puedes descargar Inno Setup gratis desde: https://jrsoftware.org/isdl.php
    echo Una vez instalado, compila 'installer.iss' para generar KognitoSync-Setup.exe.
    echo Sin embargo, la carpeta ejecutable portable ya esta lista en:
    echo cli\dist\KognitoSync\
)

pause
