@echo off
REM Script de inicio rápido para el Sistema Experto de Finanzas
REM Uso: start.bat

echo ==================================
echo   Sistema Experto de Finanzas
echo ==================================
echo.

REM Verificar que SWI-Prolog está instalado
swipl --version >nul 2>&1
if errorlevel 1 (
    echo Error: SWI-Prolog no esta instalado
    echo    Instala SWI-Prolog desde: https://www.swi-prolog.org/download/stable
    pause
    exit /b 1
)

echo [OK] SWI-Prolog encontrado
echo.

REM Verificar que Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python no esta instalado
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Verificar que el archivo Prolog existe
if not exist "asistente_finanzas.pl" (
    echo Error: No se encuentra asistente_finanzas.pl
    echo    Asegurate de estar en el directorio correcto
    pause
    exit /b 1
)

echo [OK] Archivo Prolog encontrado
echo.

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
    echo.
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
if not exist "venv\.installed" (
    echo.
    echo Instalando dependencias...
    pip install Flask==3.0.0 Flask-CORS==4.0.0 pyswip==0.2.10
    echo installed > venv\.installed
    echo.
) else (
    echo [OK] Dependencias ya instaladas
    echo.
)

echo ==================================
echo   Iniciando servidor...
echo ==================================
echo.
echo El servidor estara disponible en:
echo   http://localhost:5000
echo.
echo Endpoints:
echo   GET  http://localhost:5000/api/health
echo   POST http://localhost:5000/api/recomendaciones
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

REM Iniciar el servidor
python backend.py