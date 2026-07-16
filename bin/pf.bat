@echo off
set SCRIPT_DIR=%~dp0
py -3 "%SCRIPT_DIR%pf.py" %*
if errorlevel 9009 python "%SCRIPT_DIR%pf.py" %*
