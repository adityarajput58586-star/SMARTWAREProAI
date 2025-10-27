# SmartWare Pro - Warehouse Management System

## Overview

SmartWare Pro is a full-stack warehouse management web application built with Flask and SQLAlchemy. The system provides comprehensive inventory management capabilities including product tracking, stock history, QR/barcode scanning, interactive warehouse mapping, and data export functionality.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with Python
- **Database**: SQLAlchemy ORM with SQLite (configurable to PostgreSQL via DATABASE_URL)
- **Authentication**: Session-based authentication with hardcoded admin credentials
- **API Structure**: Server-side rendered templates with some AJAX endpoints for dynamic functionality

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with custom CSS styling
- **JavaScript**: Vanilla JS with modular components for scanner, map, and general functionality
- **Responsive Design**: Mobile-first approach with dark mode support
- **Icons**: Font Awesome for consistent iconography

### Database Schema
- **Product Model**: id, name, quantity, location, date_added with relationship to stock history
- **StockHistory Model**: id, product_id, old_quantity, new_quantity, change_reason, date_changed
- **Relationships**: One-to-many relationship between Product and StockHistory with cascade delete

## Key Components

### Authentication System
- Multi-role user system with 5 different user accounts:
  - Admin: admin@smartware.com / admin123 (full access)
  - Manager: manager@smartware.com / manager123 (most features)
  - Employee 1: employee1@smartware.com / emp123 (basic operations)
  - Employee 2: employee2@smartware.com / emp456 (basic operations)
  - Scanner User: scanner@smartware.com / scan789 (optimized for mobile scanning)
- Role-based access control with decorators for different permission levels
- Session-based login with user info and role stored in session
- Protected routes with admin, manager, and general login requirements

### Product Management
- CRUD operations for inventory items
- Real-time stock tracking with automatic history logging
- Location-based organization system
- Low stock alerts for quantities <= 5

### Stock History Tracking
- Automatic logging of quantity changes
- Detailed change history with timestamps and reasons
- Historical data visualization on product detail pages

### QR/Barcode Scanner
- Camera-based scanning using HTML5 getUserMedia API
- Manual input fallback for barcode/QR data
- Product search integration with scanned data
- Mobile-optimized camera interface

### Warehouse Map Visualization
- SVG-based interactive warehouse layout
- Product location markers with hover tooltips
- Visual representation of storage areas and pathways
- Responsive design for different screen sizes

### Data Export System
- CSV export for spreadsheet compatibility
- PDF generation using ReportLab with styled tables
- Complete inventory reporting capabilities
- Download functionality for both formats

## Data Flow

1. **User Authentication**: Login → Session creation → Dashboard access
2. **Product Operations**: Add/Edit Product → Database update → Stock history creation → Dashboard refresh
3. **Scanning Workflow**: Camera access → QR detection → Product search → Results display
4. **Map Integration**: Product location → SVG marker placement → Interactive tooltips
5. **Export Process**: Data query → Format conversion (CSV/PDF) → File download

## External Dependencies

### Backend Dependencies
- Flask: Web framework and routing
- SQLAlchemy: Database ORM and migrations
- ReportLab: PDF generation and styling
- Werkzeug: Security utilities and middleware

### Frontend Dependencies
- Bootstrap 5: UI components and responsive grid
- Font Awesome: Icon library
- HTML5-QRCode: QR/barcode scanning library
- Custom JavaScript modules for enhanced functionality

### Browser APIs
- getUserMedia: Camera access for scanning
- File API: Download functionality for exports
- LocalStorage: Theme preferences and user settings

## Deployment Strategy

### Environment Configuration
- Environment variables for database URL and session secret
- SQLite for development, PostgreSQL support for production
- Static file serving through Flask for development
- Proxy fix middleware for production deployment behind reverse proxy

### Database Management
- Automatic table creation on application startup
- Migration support through SQLAlchemy
- Connection pooling and health checks configured

### Security Considerations
- Session secret configuration via environment variables
- CSRF protection through Flask sessions
- Secure password hashing for future user management expansion
- Camera permission handling with user consent

### Performance Optimizations
- Database connection pooling with automatic recycling
- Debounced search functionality to reduce server load
- Responsive image handling for warehouse maps
- Efficient PDF generation with table streaming