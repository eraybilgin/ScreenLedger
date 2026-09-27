@echo off
chcp 65001 >nul
py -3 --version >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0kur.py"
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    python "%~dp0kur.py"
  ) else (
    echo Python 3.11 veya uzeri bulunamadi. Once python.org uzerinden kurun.
    pause
    exit /b 1
  )
)
if errorlevel 1 pause
