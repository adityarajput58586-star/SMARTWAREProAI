@echo off
REM SIFWO (smart inventry Flow warehouse operations) Database Backup Script

echo ========================================
echo SIFWO (smart inventry Flow warehouse operations) - Database Backup
echo ========================================
echo.

REM Create backups folder if it doesn't exist
if not exist "backups" mkdir backups

REM Get current date and time
set timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%

REM Check if database exists
if not exist "instance\warehouse.db" (
    echo ERROR: Database file not found!
    echo Location: instance\warehouse.db
    echo.
    pause
    exit /b 1
)

REM Create backup
echo Creating backup...
copy "instance\warehouse.db" "backups\warehouse_%timestamp%.db" >nul

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Backup created!
    echo File: backups\warehouse_%timestamp%.db
    echo.
    
    REM Show database size
    for %%A in ("instance\warehouse.db") do echo Database size: %%~zA bytes
    echo.
    
    REM Count backups
    dir /b backups\warehouse_*.db 2>nul | find /c /v "" > temp.txt
    set /p backup_count=<temp.txt
    del temp.txt
    echo Total backups: %backup_count%
    echo.
) else (
    echo.
    echo ERROR: Backup failed!
    echo.
)

pause
