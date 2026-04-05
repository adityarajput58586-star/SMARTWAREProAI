# SIFWO (smart inventry Flow warehouse operations) - Warehouse Management System

A comprehensive warehouse management system built with Flask, featuring real-time inventory tracking, smart overflow management, QR code scanning, and automated email alerts.

## Features

- **Multi-Role Authentication**: Owner, Admin, Manager, and Scanner roles with different access levels
- **Smart Inventory Management**: Auto-extend sections and intelligent overflow to adjacent storage areas
- **QR Code Scanning**: Built-in scanner for quick product lookup and stock management
- **Real-Time Alerts**: Automated email notifications for low stock (30% threshold based on max quantity)
- **Vendor Management**: Track vendors with contact information and automated alerts
- **Section Management**: Configure warehouse sections with capacity limits
- **Stock History**: Complete audit trail of all stock movements
- **Export Functionality**: Export data to CSV and PDF formats
- **Interactive Dashboard**: Real-time statistics and product overview
- **Responsive Design**: Mobile-friendly interface with Bootstrap

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```
# Option 1: SendGrid (Recommended for Render - works on free tier)
SENDGRID_API_KEY=your-sendgrid-api-key
EMAIL_USER=noreply@sifwo.com

# Option 2: SMTP (Gmail - may be blocked on some platforms)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**Note:** The system tries SendGrid first, then falls back to SMTP if SendGrid is not configured.

4. Initialize the database:
```bash
python database.py
```

5. Run the application:
```bash
python main.py
```

The app will be available at `http://localhost:5000`

## Default Login Credentials

- **Owner**: owner / owner123
- **Admin**: admin / admin123
- **Manager**: manager / manager123
- **Scanner**: scanner / scanner123

## Project Structure

```
├── app.py              # Main Flask application
├── main.py             # Application entry point
├── models.py           # Database models
├── database.py         # Database initialization
├── utils.py            # Utility functions (email alerts, etc.)
├── templates/          # HTML templates
├── static/             # CSS, JS, and static assets
└── instance/           # Database storage
```

## Key Functionality

### Smart Overflow System
When adding stock that exceeds section capacity:
1. Auto-extends the section if space is available
2. Overflows to adjacent sections if current section is full
3. Tracks overflow locations for easy retrieval

### Threshold Alerts
- Automatically calculates threshold as 30% of maximum quantity ever recorded
- Sends email alerts to vendors, managers, and admins when stock falls below threshold
- Validates email addresses before sending

### Role-Based Access
- **Owner**: Full system access, user management
- **Admin**: Product and vendor management, exports
- **Manager**: Product management, notifications
- **Scanner**: QR scanning and stock lookup only

## Technologies Used

- **Backend**: Flask, SQLAlchemy
- **Frontend**: Bootstrap 5, Font Awesome, JavaScript
- **Database**: SQLite
- **Email**: SMTP (Gmail)
- **Export**: CSV, PDF generation

## License

Proprietary - All rights reserved
