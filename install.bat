@echo off
echo ========================================
echo Smart Inventory Management System
echo Installation Script
echo ========================================
echo.

echo Installing Python dependencies...
pip install flask flask-sqlalchemy reportlab werkzeug

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To start the application, run:
echo   python main.py
echo.
echo Then open your browser to:
echo   http://localhost:5000
echo.
echo Default login:
echo   Admin: admin@smartware.com / admin123
echo   Manager: manager@smartware.com / manager123
echo.
pause
