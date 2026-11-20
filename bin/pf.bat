@echo off
"%SystemRoot%\System32\where.exe" /q py.exe
if errorlevel 1 goto use_python
py -3 "%~dp0pf.py" %*
exit /b %errorlevel%

:use_python
python "%~dp0pf.py" %*
exit /b %errorlevel%
