@echo off
setlocal

if "%~1"=="" (
  echo Usage: flash-yahboom.cmd COM6 [baudrate]
  exit /b 1
)

set "PORT=%~1"
set "BAUDRATE=%~2"

if "%BAUDRATE%"=="" set "BAUDRATE=1500000"

powershell -ExecutionPolicy Bypass -File "%~dp0flash-yahboom.ps1" -Port "%PORT%" -BaudRate %BAUDRATE%
exit /b %ERRORLEVEL%
