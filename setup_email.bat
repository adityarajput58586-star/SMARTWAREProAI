@echo off
REM SIFWO (smart inventry Flow warehouse operations) - Email Setup Script

echo ========================================
echo SIFWO (smart inventry Flow warehouse operations) - Email Setup
echo ========================================
echo.

REM Check if .env file exists
if exist ".env" (
    echo .env file already exists
    echo.
    choice /C YN /M "Do you want to overwrite it"
    if errorlevel 2 goto :skip_create
)

REM Create .env file from template
if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo .env file created from template
) else (
    echo Creating .env file...
    (
        echo # SIFWO (smart inventry Flow warehouse operations) - Email Configuration
        echo.
        echo # Gmail Configuration
        echo EMAIL_USER=your-email@gmail.com
        echo EMAIL_PASSWORD=your-app-password-here
        echo SMTP_SERVER=smtp.gmail.com
        echo SMTP_PORT=587
    ) > .env
    echo .env file created
)

:skip_create
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo.
echo 1. Open .env file in a text editor
echo 2. Replace 'your-email@gmail.com' with your Gmail address
echo 3. Get Gmail App Password:
echo    - Go to: https://myaccount.google.com/apppasswords
echo    - Enable 2-Step Verification if needed
echo    - Generate App Password for 'Mail' and 'Windows Computer'
echo    - Copy the 16-character password
echo 4. Replace 'your-app-password-here' with the App Password
echo 5. Save the .env file
echo 6. Run: python test_email.py
echo.
echo ========================================
echo.

REM Check if python-dotenv is installed
python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo python-dotenv is not installed
    echo.
    choice /C YN /M "Do you want to install it now"
    if not errorlevel 2 (
        echo.
        echo Installing python-dotenv...
        pip install python-dotenv
        echo.
        if errorlevel 0 (
            echo python-dotenv installed successfully!
        ) else (
            echo Failed to install python-dotenv
            echo Please run: pip install python-dotenv
        )
    )
) else (
    echo python-dotenv is already installed
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Edit .env file now? (opens in notepad)
choice /C YN /M "Open .env file"
if not errorlevel 2 (
    notepad .env
)

echo.
pause
