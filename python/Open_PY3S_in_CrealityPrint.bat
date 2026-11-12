@echo off
setlocal EnableExtensions

if not "%~1"=="" (
  call :launch "%~1"
  goto :done
)

echo Drag and drop a .py3s file into this window and press Enter
echo (or press Enter directly to browse for a .py3s file):
echo.
set "PY3S_INPUT="
set /p "PY3S_INPUT=PY3S File: "
if defined PY3S_INPUT goto :use_input

python "%~dp0py3s_creality_bridge.py" --pick --launch
if errorlevel 1 (
  echo.
  echo Failed to open the selected .py3s file in Creality Print 7.2.
  pause
  exit /b 1
)
goto :done

:use_input
set "PY3S_CLEAN=%PY3S_INPUT:"=%"
call :launch "%PY3S_CLEAN%"
goto :done

:launch
python "%~dp0py3s_creality_bridge.py" "%~1" --launch
if errorlevel 1 (
  echo.
  echo Failed to open "%~1" in Creality Print 7.2.
  pause
  exit /b 1
)
exit /b 0

:done
endlocal

