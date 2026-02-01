@echo off
REM AI Mentor - PowerShell Hidden Launcher Wrapper
REM This launches the PowerShell script with execution policy bypass

powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start_hidden_powershell.ps1"