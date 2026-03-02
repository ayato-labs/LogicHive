@echo off
setlocal
chcp 65001 > nul

echo =========================================
echo LogicHive Deployment Launcher
echo =========================================
echo [1] Deploy Edge to GitHub (Release EXE)
echo [2] Deploy Business Portal / Hub to GCP (Cloud Run)
echo [0] Exit
echo =========================================

set /p target="Select deployment option (0-2): "

if "%target%"=="1" (
    echo.
    echo Starting Edge Deployment...
    uv run python ci_cd\cd_github.py
) else if "%target%"=="2" (
    echo.
    echo Starting Cloud (GCP) Deployment...
    uv run python ci_cd\deploy_cloud.py
) else if "%target%"=="0" (
    echo Exiting...
) else (
    echo Invalid option selected.
)

pause
