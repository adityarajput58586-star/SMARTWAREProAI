import os
import logging
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

# Configure logging
logging.basicConfig(level=logging.DEBUG)

from database import db

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
from models import Product, StockHistory, Vendor, WarehouseSection, StockBatch, NotificationLog, WarehouseConfig, AuthorizedUser, SectionCapacityLog
from utils import suggest_storage_locations, check_and_trigger_alerts, update_section_usage

# Owner credentials (hardcoded)
OWNER_EMAIL = "owner@smartwarepro.com"
OWNER_PASSWORD = "owner2024"

# Create tables and initialize data
with app.app_context():
    db.create_all()
    
    # Initialize owner and default users if not exists
    if AuthorizedUser.query.count() == 0:
        # Add default users
        default_users = [
            AuthorizedUser(
                company_name="Demo Company",
                email="admin@smartware.com",
                password="admin123",
                name="System Administrator",
                role="admin"
            ),
            AuthorizedUser(
                company_name="Demo Company",
                email="manager@smartware.com",
                password="manager123",
                name="Warehouse Manager",
                role="manager"
            ),
            AuthorizedUser(
                company_name="Demo Company",
                email="employee1@smartware.com",
                password="emp123",
                name="John Smith",
                role="employee"
            ),
            AuthorizedUser(
                company_name="Demo Company",
                email="scanner@smartware.com",
                password="scan789",
                name="Mobile Scanner User",
                role="scanner"
            )
        ]
        for user in default_users:
            db.session.add(user)
        db.session.commit()
        print("Default authorized users created")
    
    # Initialize warehouse config if not exists
    if WarehouseConfig.query.count() == 0:
        config = WarehouseConfig(
            total_space=1000,
            space_unit='units',
            warehouse_name='Main Warehouse'
        )
        db.session.add(config)
        db.session.commit()
        print("Warehouse configuration initialized")
    
    # Initialize default warehouse sections if none exist
    if WarehouseSection.query.count() == 0:
        default_sections = [
            WarehouseSection(name="Section A", capacity=200, x_coordinate=50, y_coordinate=50, width=180, height=150, color='#bbdefb'),
            WarehouseSection(name="Section B", capacity=200, x_coordinate=250, y_coordinate=50, width=180, height=150, color='#c5cae9'),
            WarehouseSection(name="Section C", capacity=150, x_coordinate=450, y_coordinate=50, width=180, height=150, color='#c8e6c9'),
            WarehouseSection(name="Section D", capacity=150, x_coordinate=50, y_coordinate=220, width=180, height=150, color='#fff9c4'),
            WarehouseSection(name="Section E", capacity=100, x_coordinate=250, y_coordinate=220, width=180, height=150, color='#ffccbc'),
        ]
        for section in default_sections:
            db.session.add(section)
        db.session.commit()
        print("Default warehouse sections created")

# User credentials with roles (kept for backward compatibility, but will be replaced by AuthorizedUser)
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

def owner_required(f):
    """Decorator to require owner role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'owner':
            flash('Owner access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Decorator to block owner from staff routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        if session.get('role') == 'owner':
            flash('This section is for staff only. You are logged in as owner.', 'error')
            return redirect(url_for('owner_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        login_type = request.form.get('login_type', 'user')
        
        # Check if owner login
        if login_type == 'owner':
            if email == OWNER_EMAIL and password == OWNER_PASSWORD:
                session['logged_in'] = True
                session['email'] = email
                session['role'] = 'owner'
                session['name'] = 'System Owner'
                flash(f'Welcome, System Owner!', 'success')
                return redirect(url_for('owner_dashboard'))
            else:
                flash('Invalid owner credentials.', 'error')
        else:
            # Check in AuthorizedUser database
            user = AuthorizedUser.query.filter_by(email=email, is_active=True).first()
            
            if user and user.password == password:
                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                session['logged_in'] = True
                session['email'] = email
                session['role'] = user.role
                session['name'] = user.name
                session['company_name'] = user.company_name
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials or account not authorized. Contact system owner.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@staff_required
def dashboard():
    """Main dashboard showing all products"""
    # Redirect owner to owner dashboard
    if session.get('role') == 'owner':
        return redirect(url_for('owner_dashboard'))
    
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
@staff_required
def add_product():
    """Add new product with smart location suggestions and overflow handling"""
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = int(request.form.get('quantity', 0))
        unit_type = request.form.get('unit_type', 'boxes')
        vendor_id = request.form.get('vendor_id')
        auto_reorder = request.form.get('auto_reorder') == 'on'
        preferred_section_id = request.form.get('preferred_section')
        
        if name and quantity > 0:
            # Use smart storage allocation with overflow handling
            suggestions = suggest_storage_locations(
                name, 
                quantity, 
                db, 
                preferred_section_id=int(preferred_section_id) if preferred_section_id else None,
                product_id=None  # Will be set after product creation
            )
            
            # Create product
            product = Product(
                name=name,
                quantity=quantity,
                location=', '.join([s[0].name for s in suggestions if s[0]]),  # Legacy field
                unit_type=unit_type,
                vendor_id=int(vendor_id) if vendor_id else None,
                auto_reorder_enabled=auto_reorder
            )
            db.session.add(product)
            db.session.flush()  # Get product ID
            
            # Create stock batches based on suggestions
            placement_info = []
            for suggestion in suggestions:
                if len(suggestion) >= 3:
                    section, qty_to_store, overflow_info = suggestion[0], suggestion[1], suggestion[2]
                else:
                    section, qty_to_store = suggestion[0], suggestion[1]
                    overflow_info = None
                
                if section:  # If section exists
                    batch = StockBatch(
                        product_id=product.id,
                        section_id=section.id,
                        quantity=qty_to_store,
                        arrival_date=datetime.utcnow()
                    )
                    db.session.add(batch)
                    
                    # Build placement info message
                    if overflow_info:
                        placement_info.append(f"{overflow_info}: {qty_to_store} {unit_type}")
                    else:
                        placement_info.append(f"{qty_to_store} {unit_type} → {section.name}")
                else:
                    # No section available, show warning
                    if overflow_info:
                        placement_info.append(f"⚠️ {overflow_info}")
            
            # Add initial stock history entry
            stock_history = StockHistory(
                product_id=product.id,
                old_quantity=0,
                new_quantity=quantity,
                change_reason='Initial stock',
                change_type='in'
            )
            db.session.add(stock_history)
            
            # Update section usage
            update_section_usage(db)
            
            db.session.commit()
            
            # Show detailed placement information to user
            flash(f'Product "{name}" added successfully! Placement: {" | ".join(placement_info)}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Please fill in all required fields with valid quantity.', 'error')
    
    # Get vendors and sections for form
    vendors = Vendor.query.filter_by(is_active=True).all()
    sections = WarehouseSection.query.order_by(WarehouseSection.name).all()
    
    return render_template('add_product.html', vendors=vendors, sections=sections)

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
@staff_required
def edit_product(product_id):
    """Edit product details and check for threshold alerts"""
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
        change_type = 'in' if new_quantity > old_quantity else 'out'
        quantity_diff = abs(new_quantity - old_quantity)
        
        # If stock decreased, reduce from batches using FIFO
        if new_quantity < old_quantity:
            from utils import reduce_stock_from_batches
            affected_sections = reduce_stock_from_batches(product, quantity_diff, db)
            
            section_info = ', '.join([f"{s['reduced']} from {s['section']}" for s in affected_sections])
            change_reason = f'Stock out: {quantity_diff} units ({section_info})'
        else:
            change_reason = f'Stock in: {quantity_diff} units'
        
        product.quantity = new_quantity
        stock_history = StockHistory(
            product_id=product.id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            change_reason=change_reason,
            change_type=change_type
        )
        db.session.add(stock_history)
        
        # Update section usage after batch changes
        update_section_usage(db)
        
        # Check if we need to trigger alerts
        if new_quantity < old_quantity:  # Stock decreased
            check_and_trigger_alerts(product, db)
    
    db.session.commit()
    flash(f'Product "{name}" updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/product/<int:product_id>')
@staff_required
def product_detail(product_id):
    """Product detail page with stock history and batch information"""
    product = Product.query.get_or_404(product_id)
    stock_history = StockHistory.query.filter_by(product_id=product_id).order_by(StockHistory.date_changed.desc()).all()
    stock_batches = StockBatch.query.filter_by(product_id=product_id).order_by(StockBatch.arrival_date.desc()).all()
    
    # Get batch details with section info
    batch_details = []
    for batch in stock_batches:
        batch_details.append({
            'batch': batch,
            'section': batch.section
        })
    
    return render_template('product_detail.html', 
                         product=product, 
                         stock_history=stock_history,
                         batch_details=batch_details)

@app.route('/receive_stock/<int:product_id>', methods=['GET', 'POST'])
@staff_required
def receive_stock(product_id):
    """Receive new stock for existing product with smart placement and overflow handling"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 0))
        preferred_section_id = request.form.get('preferred_section')
        
        if quantity > 0:
            # Get smart location suggestions with overflow handling
            suggestions = suggest_storage_locations(
                product.name, 
                quantity, 
                db,
                preferred_section_id=int(preferred_section_id) if preferred_section_id else None,
                product_id=product.id
            )
            
            old_quantity = product.quantity
            product.quantity += quantity
            
            # Create stock batches based on suggestions
            placement_info = []
            for suggestion in suggestions:
                if len(suggestion) >= 3:
                    section, qty_to_store, overflow_info = suggestion[0], suggestion[1], suggestion[2]
                else:
                    section, qty_to_store = suggestion[0], suggestion[1]
                    overflow_info = None
                
                if section:  # If section exists
                    batch = StockBatch(
                        product_id=product.id,
                        section_id=section.id,
                        quantity=qty_to_store,
                        arrival_date=datetime.utcnow()
                    )
                    db.session.add(batch)
                    
                    if overflow_info:
                        placement_info.append(f"{overflow_info}: {qty_to_store} {product.unit_type}")
                    else:
                        placement_info.append(f"{qty_to_store} {product.unit_type} → {section.name}")
                else:
                    if overflow_info:
                        placement_info.append(f"⚠️ {overflow_info}")
            
            # Add stock history
            stock_history = StockHistory(
                product_id=product.id,
                old_quantity=old_quantity,
                new_quantity=product.quantity,
                change_reason=f'Stock received: {quantity} {product.unit_type}',
                change_type='in'
            )
            db.session.add(stock_history)
            
            # Update section usage
            update_section_usage(db)
            
            db.session.commit()
            
            flash(f'Received {quantity} {product.unit_type} of "{product.name}". Placement: {" | ".join(placement_info)}', 'success')
            
            # Check if we need to send alerts (stock might have been replenished)
            return redirect(url_for('product_detail', product_id=product_id))
        else:
            flash('Please enter a valid quantity.', 'error')
    
    # Show available sections
    sections = WarehouseSection.query.all()
    return render_template('receive_stock.html', product=product, sections=sections)

@app.route('/remove_stock/<int:product_id>', methods=['GET', 'POST'])
@staff_required
def remove_stock(product_id):
    """Remove stock (sale/usage) with FIFO tracking"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 0))
        reason = request.form.get('reason', 'Stock removed')
        
        if quantity > 0 and quantity <= product.quantity:
            old_quantity = product.quantity
            
            # Reduce stock from batches using FIFO
            from utils import reduce_stock_from_batches
            affected_sections = reduce_stock_from_batches(product, quantity, db)
            
            # Update product quantity
            product.quantity -= quantity
            
            # Create detailed change reason
            section_info = ', '.join([f"{s['reduced']} from {s['section']}" for s in affected_sections])
            change_reason = f'{reason}: {quantity} {product.unit_type} ({section_info})'
            
            # Add stock history
            stock_history = StockHistory(
                product_id=product.id,
                old_quantity=old_quantity,
                new_quantity=product.quantity,
                change_reason=change_reason,
                change_type='out'
            )
            db.session.add(stock_history)
            
            # Update section usage (space freed up!)
            update_section_usage(db)
            
            db.session.commit()
            
            # Check if we need to trigger alerts
            check_and_trigger_alerts(product, db)
            
            flash(f'Removed {quantity} {product.unit_type} of "{product.name}". Freed space: {section_info}', 'success')
            return redirect(url_for('product_detail', product_id=product_id))
        elif quantity > product.quantity:
            flash(f'Cannot remove {quantity} units. Only {product.quantity} available.', 'error')
        else:
            flash('Please enter a valid quantity.', 'error')
    
    # Show current batches
    batches = StockBatch.query.filter_by(product_id=product_id).order_by(StockBatch.arrival_date.asc()).all()
    batch_details = []
    for batch in batches:
        batch_details.append({
            'batch': batch,
            'section': batch.section
        })
    
    return render_template('remove_stock.html', product=product, batch_details=batch_details)

@app.route('/scan', methods=['GET', 'POST'])
@staff_required
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
@staff_required
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

@app.route('/api/warehouse_map')
@staff_required
def warehouse_map_data():
    """API endpoint to get warehouse map data"""
    sections = WarehouseSection.query.all()
    config = WarehouseConfig.query.first()
    
    sections_data = []
    for section in sections:
        # Get products in this section
        batches = StockBatch.query.filter_by(section_id=section.id).all()
        products_in_section = []
        
        for batch in batches:
            if batch.quantity > 0:
                products_in_section.append({
                    'name': batch.product.name,
                    'quantity': batch.quantity,
                    'unit': batch.product.unit_type
                })
        
        sections_data.append({
            'id': section.id,
            'name': section.name,
            'capacity': section.capacity,
            'current_usage': section.current_usage,
            'available_space': section.available_space,
            'usage_percentage': round(section.usage_percentage, 1),
            'x': section.x_coordinate,
            'y': section.y_coordinate,
            'width': section.width,
            'height': section.height,
            'color': section.color,
            'products': products_in_section
        })
    
    return jsonify({
        'sections': sections_data,
        'config': {
            'total_space': config.total_space if config else 1000,
            'used_space': config.used_space if config else 0,
            'available_space': config.available_space if config else 1000,
            'warehouse_name': config.warehouse_name if config else 'Main Warehouse'
        }
    })

@app.route('/api/sections')
@staff_required
def get_sections():
    """API endpoint to get all sections for dropdown"""
    sections = WarehouseSection.query.order_by(WarehouseSection.name).all()
    
    sections_data = []
    for section in sections:
        sections_data.append({
            'id': section.id,
            'name': section.name,
            'capacity': section.capacity,
            'current_usage': section.current_usage,
            'available_space': section.available_space,
            'usage_percentage': round(section.usage_percentage, 1)
        })
    
    return jsonify(sections_data)

@app.route('/vendors')
@manager_or_admin_required
def vendors():
    """Vendor management page"""
    vendors = Vendor.query.all()
    return render_template('vendors.html', vendors=vendors)

@app.route('/vendor/add', methods=['POST'])
@manager_or_admin_required
def add_vendor():
    """Add new vendor"""
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    
    if name and email:
        vendor = Vendor(
            name=name,
            email=email,
            phone=phone,
            address=address
        )
        db.session.add(vendor)
        db.session.commit()
        flash(f'Vendor "{name}" added successfully!', 'success')
    else:
        flash('Please provide vendor name and email.', 'error')
    
    return redirect(url_for('vendors'))

@app.route('/vendor/edit/<int:vendor_id>', methods=['POST'])
@manager_or_admin_required
def edit_vendor(vendor_id):
    """Edit vendor details"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    vendor.name = request.form.get('name')
    vendor.email = request.form.get('email')
    vendor.phone = request.form.get('phone')
    vendor.address = request.form.get('address')
    vendor.is_active = request.form.get('is_active') == 'on'
    
    db.session.commit()
    flash(f'Vendor "{vendor.name}" updated successfully!', 'success')
    return redirect(url_for('vendors'))

@app.route('/vendor/delete/<int:vendor_id>')
@admin_required
def delete_vendor(vendor_id):
    """Delete vendor"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    # Check if vendor has products
    if vendor.products:
        flash(f'Cannot delete vendor "{vendor.name}" - it has associated products.', 'error')
    else:
        db.session.delete(vendor)
        db.session.commit()
        flash(f'Vendor "{vendor.name}" deleted successfully!', 'success')
    
    return redirect(url_for('vendors'))

@app.route('/sections')
@manager_or_admin_required
def warehouse_sections():
    """Warehouse sections management page"""
    sections = WarehouseSection.query.all()
    config = WarehouseConfig.query.first()
    if not config:
        config = WarehouseConfig(total_space=1000)
        db.session.add(config)
        db.session.commit()
    return render_template('sections.html', sections=sections, config=config)

@app.route('/section/add', methods=['POST'])
@manager_or_admin_required
def add_section():
    """Add new warehouse section with space validation"""
    name = request.form.get('name')
    capacity = int(request.form.get('capacity', 0))
    x_coord = float(request.form.get('x_coordinate', 0))
    y_coord = float(request.form.get('y_coordinate', 0))
    width = float(request.form.get('width', 100))
    height = float(request.form.get('height', 100))
    color = request.form.get('color', '#e3f2fd')
    
    if name and capacity > 0:
        # Check if adding this section exceeds total warehouse space
        config = WarehouseConfig.query.first()
        if config and (config.used_space + capacity) > config.total_space:
            flash(f'Cannot add section: Would exceed total warehouse space. Available: {config.available_space} units', 'error')
            return redirect(url_for('warehouse_sections'))
        
        section = WarehouseSection(
            name=name,
            capacity=capacity,
            x_coordinate=x_coord,
            y_coordinate=y_coord,
            width=width,
            height=height,
            color=color
        )
        db.session.add(section)
        db.session.commit()
        flash(f'Section "{name}" added successfully!', 'success')
    else:
        flash('Please provide valid section details.', 'error')
    
    return redirect(url_for('warehouse_sections'))

@app.route('/section/edit/<int:section_id>', methods=['POST'])
@manager_or_admin_required
def edit_section(section_id):
    """Edit warehouse section with space validation"""
    section = WarehouseSection.query.get_or_404(section_id)
    
    old_capacity = section.capacity
    new_name = request.form.get('name')
    new_capacity = int(request.form.get('capacity', 0))
    x_coord = float(request.form.get('x_coordinate', section.x_coordinate))
    y_coord = float(request.form.get('y_coordinate', section.y_coordinate))
    width = float(request.form.get('width', section.width))
    height = float(request.form.get('height', section.height))
    color = request.form.get('color', section.color)
    
    # Check if capacity change exceeds total warehouse space
    config = WarehouseConfig.query.first()
    capacity_diff = new_capacity - old_capacity
    if config and capacity_diff > 0 and (config.used_space + capacity_diff) > config.total_space:
        flash(f'Cannot increase capacity: Would exceed total warehouse space. Available: {config.available_space} units', 'error')
        return redirect(url_for('warehouse_sections'))
    
    # Check if new capacity is less than current usage
    if new_capacity < section.current_usage:
        flash(f'Cannot reduce capacity below current usage ({section.current_usage} units)', 'error')
        return redirect(url_for('warehouse_sections'))
    
    section.name = new_name
    section.capacity = new_capacity
    section.x_coordinate = x_coord
    section.y_coordinate = y_coord
    section.width = width
    section.height = height
    section.color = color
    
    db.session.commit()
    flash(f'Section "{section.name}" updated successfully!', 'success')
    return redirect(url_for('warehouse_sections'))

@app.route('/section/delete/<int:section_id>')
@admin_required
def delete_section(section_id):
    """Delete warehouse section"""
    section = WarehouseSection.query.get_or_404(section_id)
    
    # Check if section has stock
    if section.current_usage > 0:
        flash(f'Cannot delete section "{section.name}" - it contains {section.current_usage} units of stock', 'error')
    else:
        db.session.delete(section)
        db.session.commit()
        flash(f'Section "{section.name}" deleted successfully!', 'success')
    
    return redirect(url_for('warehouse_sections'))

@app.route('/warehouse/config', methods=['GET', 'POST'])
@admin_required
def warehouse_config():
    """Warehouse configuration page"""
    config = WarehouseConfig.query.first()
    if not config:
        config = WarehouseConfig(total_space=1000)
        db.session.add(config)
        db.session.commit()
    
    if request.method == 'POST':
        new_total_space = int(request.form.get('total_space', 1000))
        space_unit = request.form.get('space_unit', 'units')
        warehouse_name = request.form.get('warehouse_name', 'Main Warehouse')
        
        # Check if new total space is less than currently used space
        if new_total_space < config.used_space:
            flash(f'Cannot set total space below currently used space ({config.used_space} {space_unit})', 'error')
        else:
            config.total_space = new_total_space
            config.space_unit = space_unit
            config.warehouse_name = warehouse_name
            db.session.commit()
            flash('Warehouse configuration updated successfully!', 'success')
        
        return redirect(url_for('warehouse_config'))
    
    sections = WarehouseSection.query.all()
    return render_template('warehouse_config.html', config=config, sections=sections)

@app.route('/notifications')
@manager_or_admin_required
def notifications():
    """View notification logs"""
    logs = NotificationLog.query.order_by(NotificationLog.sent_date.desc()).limit(100).all()
    return render_template('notifications.html', logs=logs)

@app.route('/notifications/delete_all', methods=['POST'])
@manager_or_admin_required
def delete_all_notifications():
    """Delete all notification logs"""
    try:
        count = NotificationLog.query.delete()
        db.session.commit()
        flash(f'Successfully deleted {count} notification(s).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting notifications: {str(e)}', 'error')
    return redirect(url_for('notifications'))

@app.route('/product/<int:product_id>/toggle_autoreorder', methods=['POST'])
@manager_or_admin_required
def toggle_autoreorder(product_id):
    """Toggle auto-reorder for a product"""
    product = Product.query.get_or_404(product_id)
    
    if not product.vendor:
        flash('Cannot enable auto-reorder: No vendor assigned to this product.', 'error')
    else:
        product.auto_reorder_enabled = not product.auto_reorder_enabled
        db.session.commit()
        
        status = "enabled" if product.auto_reorder_enabled else "disabled"
        flash(f'Auto-reorder {status} for "{product.name}".', 'success')
    
    return redirect(url_for('product_detail', product_id=product_id))

# ============= OWNER ROUTES =============

@app.route('/owner/dashboard')
@owner_required
def owner_dashboard():
    """Owner dashboard showing all authorized users"""
    users = AuthorizedUser.query.order_by(AuthorizedUser.created_at.desc()).all()
    
    # Get statistics
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    companies = len(set([u.company_name for u in users]))
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'companies': companies
    }
    
    return render_template('owner_dashboard.html', users=users, stats=stats)

@app.route('/owner/user/add', methods=['GET', 'POST'])
@owner_required
def owner_add_user():
    """Add new authorized user"""
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        name = request.form.get('name')
        role = request.form.get('role')
        auto_generate = request.form.get('auto_generate') == 'on'
        
        # Check if email already exists
        if AuthorizedUser.query.filter_by(email=email).first():
            flash(f'Email "{email}" already exists in the system.', 'error')
            return redirect(url_for('owner_add_user'))
        
        if auto_generate:
            password = AuthorizedUser.generate_unique_password()
        else:
            password = request.form.get('password')
            if not password:
                flash('Please provide a password or enable auto-generate.', 'error')
                return redirect(url_for('owner_add_user'))
        
        user = AuthorizedUser(
            company_name=company_name,
            email=email,
            password=password,
            name=name,
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'User "{name}" added successfully! Password: {password}', 'success')
        return redirect(url_for('owner_dashboard'))
    
    return render_template('owner_add_user.html')

@app.route('/owner/user/edit/<int:user_id>', methods=['GET', 'POST'])
@owner_required
def owner_edit_user(user_id):
    """Edit authorized user"""
    user = AuthorizedUser.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.company_name = request.form.get('company_name')
        user.email = request.form.get('email')
        user.name = request.form.get('name')
        user.role = request.form.get('role')
        user.is_active = request.form.get('is_active') == 'on'
        
        # Only update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.password = new_password
        
        db.session.commit()
        flash(f'User "{user.name}" updated successfully!', 'success')
        return redirect(url_for('owner_dashboard'))
    
    return render_template('owner_edit_user.html', user=user)

@app.route('/owner/user/delete/<int:user_id>')
@owner_required
def owner_delete_user(user_id):
    """Delete authorized user"""
    user = AuthorizedUser.query.get_or_404(user_id)
    name = user.name
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User "{name}" deleted successfully!', 'success')
    return redirect(url_for('owner_dashboard'))

@app.route('/owner/generate_password')
@owner_required
def owner_generate_password():
    """Generate a unique password (API endpoint)"""
    password = AuthorizedUser.generate_unique_password()
    return jsonify({'password': password})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
