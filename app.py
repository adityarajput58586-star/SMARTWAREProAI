import os
import logging
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "smartware-pro-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///warehouse.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import Product, StockHistory

# Create tables
with app.app_context():
    db.create_all()

# User credentials with roles
USERS = {
    "admin@smartware.com": {
        "password": "admin123",
        "role": "admin",
        "name": "System Administrator"
    },
    "manager@smartware.com": {
        "password": "manager123",
        "role": "manager",
        "name": "Warehouse Manager"
    },
    "employee1@smartware.com": {
        "password": "emp123",
        "role": "employee",
        "name": "John Smith"
    },
    "employee2@smartware.com": {
        "password": "emp456",
        "role": "employee",
        "name": "Sarah Johnson"
    },
    "scanner@smartware.com": {
        "password": "scan789",
        "role": "scanner",
        "name": "Mobile Scanner User"
    }
}

def login_required(f):
    """Decorator to require login for protected routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def manager_or_admin_required(f):
    """Decorator to require manager or admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') not in ['admin', 'manager']:
            flash('Manager or admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in USERS and USERS[email]['password'] == password:
            user_data = USERS[email]
            session['logged_in'] = True
            session['email'] = email
            session['role'] = user_data['role']
            session['name'] = user_data['name']
            flash(f'Welcome back, {user_data["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Main dashboard showing all products"""
    search = request.args.get('search', '')
    location_filter = request.args.get('location', '')
    
    # Base query
    query = Product.query
    
    # Apply filters
    if search:
        query = query.filter(Product.name.contains(search))
    if location_filter:
        query = query.filter(Product.location.contains(location_filter))
    
    products = query.order_by(Product.date_added.desc()).all()
    
    # Get low stock products (quantity <= 5)
    low_stock_products = Product.query.filter(Product.quantity <= 5).all()
    
    # Get unique locations for filter dropdown
    locations = db.session.query(Product.location).distinct().all()
    locations = [loc[0] for loc in locations if loc[0]]
    
    return render_template('index.html', 
                         products=products, 
                         low_stock_products=low_stock_products,
                         locations=locations,
                         search=search,
                         location_filter=location_filter)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add new product"""
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = int(request.form.get('quantity', 0))
        location = request.form.get('location')
        
        if name and location:
            product = Product(
                name=name,
                quantity=quantity,
                location=location
            )
            db.session.add(product)
            db.session.commit()
            
            # Add initial stock history entry
            stock_history = StockHistory(
                product_id=product.id,
                old_quantity=0,
                new_quantity=quantity,
                change_reason='Initial stock'
            )
            db.session.add(stock_history)
            db.session.commit()
            
            flash(f'Product "{name}" added successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Please fill in all required fields.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:product_id>')
@manager_or_admin_required
def delete_product(product_id):
    """Delete product by ID"""
    product = Product.query.get_or_404(product_id)
    
    # Delete associated stock history
    StockHistory.query.filter_by(product_id=product_id).delete()
    
    # Delete the product
    db.session.delete(product)
    db.session.commit()
    
    flash(f'Product "{product.name}" deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    """Edit product details"""
    product = Product.query.get_or_404(product_id)
    
    name = request.form.get('name')
    new_quantity = int(request.form.get('quantity', 0))
    location = request.form.get('location')
    
    old_quantity = product.quantity
    
    # Update product
    product.name = name
    product.location = location
    
    # If quantity changed, create stock history entry
    if new_quantity != old_quantity:
        product.quantity = new_quantity
        stock_history = StockHistory(
            product_id=product.id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            change_reason='Manual update'
        )
        db.session.add(stock_history)
    
    db.session.commit()
    flash(f'Product "{name}" updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    """Product detail page with stock history"""
    product = Product.query.get_or_404(product_id)
    stock_history = StockHistory.query.filter_by(product_id=product_id).order_by(StockHistory.date_changed.desc()).all()
    
    return render_template('product_detail.html', product=product, stock_history=stock_history)

@app.route('/scan', methods=['GET', 'POST'])
@login_required
def scan_product():
    """QR/Barcode scanner page"""
    if request.method == 'POST':
        scanned_data = request.form.get('scanned_data', '')
        if scanned_data:
            # Search for products matching the scanned data
            products = Product.query.filter(Product.name.contains(scanned_data)).all()
            return render_template('index.html', 
                                 products=products, 
                                 search=scanned_data,
                                 scanned=True)
    
    return redirect(url_for('dashboard'))

@app.route('/export_csv')
@manager_or_admin_required
def export_csv():
    """Export inventory to CSV"""
    products = Product.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Quantity', 'Location', 'Date Added'])
    
    # Write data
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.quantity,
            product.location,
            product.date_added.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@app.route('/export_pdf')
@manager_or_admin_required
def export_pdf():
    """Export inventory to PDF"""
    products = Product.query.all()
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=1,
        spaceAfter=30
    )
    
    # Build content
    content = []
    
    # Title
    title = Paragraph("SmartWare Pro - Inventory Report", title_style)
    content.append(title)
    content.append(Spacer(1, 12))
    
    # Date
    date_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    date_para = Paragraph(date_text, styles['Normal'])
    content.append(date_para)
    content.append(Spacer(1, 12))
    
    # Table data
    data = [['ID', 'Product Name', 'Quantity', 'Location', 'Date Added']]
    
    for product in products:
        data.append([
            str(product.id),
            product.name,
            str(product.quantity),
            product.location,
            product.date_added.strftime('%Y-%m-%d')
        ])
    
    # Create table
    table = Table(data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 2*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(table)
    
    # Build PDF
    doc.build(content)
    
    # Create response
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

@app.route('/api/products_map')
@login_required
def products_map():
    """API endpoint to get products for warehouse map"""
    products = Product.query.all()
    products_data = []
    
    for product in products:
        # Generate pseudo-coordinates based on location for demo
        # In real implementation, you'd store actual coordinates
        location_hash = hash(product.location) % 1000
        x = (location_hash % 100) / 100 * 800 + 50  # Scale to map size
        y = ((location_hash // 100) % 100) / 100 * 600 + 50
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'quantity': product.quantity,
            'location': product.location,
            'x': x,
            'y': y,
            'low_stock': product.quantity <= 5
        })
    
    return jsonify(products_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
