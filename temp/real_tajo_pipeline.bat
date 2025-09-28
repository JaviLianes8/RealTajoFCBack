@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ========= Config =========
set "BASE=https://realtajoback-b8a4dxbxdkhtgham.westeurope-01.azurewebsites.net/api/v1"
set "CLASS_LONG=C:\workspace_python\RealTajoFc\temp\Clasificación.pdf"
set "CAL_LONG=C:\workspace_python\RealTajoFc\temp\Calendario.pdf"
set "GOAL_LONG=C:\workspace_python\RealTajoFc\temp\Goleadores.pdf"
REM =========================

REM Cambiar a UTF-8 ayuda en salidas; no es obligatorio
chcp 65001 >nul

REM Resolver rutas a formato corto 8.3 para evitar problemas con acentos
set "CLASS_FILE="
set "CAL_FILE="
set "GOAL_FILE="

for %%I in ("%CLASS_LONG%") do set "CLASS_FILE=%%~sfI"
for %%I in ("%CAL_LONG%") do set "CAL_FILE=%%~sfI"
for %%I in ("%GOAL_LONG%") do set "GOAL_FILE=%%~sfI"

REM Validaciones básicas
if not exist "%CLASS_LONG%" echo [WARN] No existe: %CLASS_LONG%
if not exist "%CAL_LONG%"   echo [WARN] No existe: %CAL_LONG%"
if not exist "%GOAL_LONG%"  echo [WARN] No existe: %GOAL_LONG%"

echo ==========================================================
echo 1) GET /status
curl -s -S -X GET "%BASE%/status" || echo [ERROR] /status fallo
echo.
echo ----------------------------------------------------------

echo 2) PUT /classification
curl -s -S -X PUT "%BASE%/classification" -F "file=@%CLASS_FILE%;type=application/pdf" ^
  || echo [ERROR] /classification fallo al subir "%CLASS_LONG%"
echo.
echo 3) GET /classification
curl -s -S -X GET "%BASE%/classification" || echo [ERROR] /classification fallo al leer
echo.
echo ----------------------------------------------------------

echo 4) PUT /real-tajo/calendar
curl -s -S -X PUT "%BASE%/real-tajo/calendar" -F "file=@%CAL_FILE%;type=application/pdf" ^
  || echo [ERROR] /real-tajo/calendar fallo al subir "%CAL_LONG%"
echo.
echo 5) GET /real-tajo/calendar
curl -s -S -X GET "%BASE%/real-tajo/calendar" || echo [ERROR] /real-tajo/calendar fallo al leer
echo.
echo ----------------------------------------------------------

echo 6) PUT /top-scorers
curl -s -S -X PUT "%BASE%/top-scorers" -F "file=@%GOAL_FILE%;type=application/pdf" ^
  || echo [ERROR] /top-scorers fallo al subir "%GOAL_LONG%"
echo.
echo 7) GET /top-scorers
curl -s -S -X GET "%BASE%/top-scorers" || echo [ERROR] /top-scorers fallo al leer
echo.
echo ==========================================================

echo Hecho.
endlocal
