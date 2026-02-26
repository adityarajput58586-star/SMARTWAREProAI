from database import db
from datetime import datetime, timezone, timedelta
import secrets
import string

def get_ist_time():
    """Get current time in IST (UTC+5:30)"""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)

class AuthorizedUser(db.Model):
    """Owner-managed user credentials"""
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)  # Plain text for owner to see
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager, employee, scanner
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(50), default='owner')
    last_login = db.Column(db.DateTime)
    
    @staticmethod
    def generate_unique_password():
        """Generate a unique 8-character password"""
        while True:
            # Generate password with mix of upper, lower, numbers, special chars
            chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + '!@#$%^&*'
            password = ''.join(secrets.choice(chars) for _ in range(8))
            
            # Ensure it has at least one of each type
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in '!@#$%^&*' for c in password)
            
            if has_upper and has_lower and has_digit and has_special:
                # Check if password already exists
                if not AuthorizedUser.query.filter_by(password=password).first():
                    return password
    
    def __repr__(self):
        return f'<AuthorizedUser {self.email}>'

class Vendor(db.Model):
    """Vendor model for supplier management"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Relationship to products
    products = db.relationship('Product', backref='vendor', lazy=True)
    
    def __repr__(self):
        return f'<Vendor {self.name}>'

class WarehouseConfig(db.Model):
    """Warehouse configuration for total space management"""
    id = db.Column(db.Integer, primary_key=True)
    total_space = db.Column(db.Integer, nullable=False, default=1000)  # Total warehouse capacity
    space_unit = db.Column(db.String(20), default='sq_meters')  # sq_meters, sq_feet, etc.
    warehouse_name = db.Column(db.String(100), default='Main Warehouse')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    @property
    def used_space(self):
        """Calculate total used space from all sections"""
        sections = WarehouseSection.query.all()
        return sum(section.capacity for section in sections)
    
    @property
    def available_space(self):
        """Calculate available space for new sections"""
        return self.total_space - self.used_space
    
    @property
    def usage_percentage(self):
        """Calculate warehouse usage percentage"""
        if self.total_space == 0:
            return 0
        return (self.used_space / self.total_space) * 100
    
    def __repr__(self):
        return f'<WarehouseConfig {self.warehouse_name}>'

class WarehouseSection(db.Model):
    """Warehouse section model for location capacity management"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Section A", "Section B"
    capacity = db.Column(db.Integer, nullable=False)  # Maximum boxes/units
    current_usage = db.Column(db.Integer, default=0)  # Current boxes/units stored
    x_coordinate = db.Column(db.Float, default=0)  # For warehouse map positioning
    y_coordinate = db.Column(db.Float, default=0)  # For warehouse map positioning
    width = db.Column(db.Float, default=100)  # Visual width on map
    height = db.Column(db.Float, default=100)  # Visual height on map
    color = db.Column(db.String(20), default='#e3f2fd')  # Section color on map
    
    # Relationship to stock batches
    stock_batches = db.relationship('StockBatch', backref='section', lazy=True)
    
    @property
    def available_space(self):
        """Calculate available space in section"""
        return self.capacity - self.current_usage
    
    @property
    def usage_percentage(self):
        """Calculate usage percentage"""
        if self.capacity == 0:
            return 0
        return (self.current_usage / self.capacity) * 100
    
    def __repr__(self):
        return f'<WarehouseSection {self.name}>'

class Product(db.Model):
    """Product model for inventory items"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(100), nullable=False)  # Legacy field, kept for compatibility
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # New fields for enhanced functionality
    unit_type = db.Column(db.String(20), default='boxes')  # boxes, units, kg, etc.
    threshold_percentage = db.Column(db.Integer, default=30)  # Alert threshold
    auto_reorder_enabled = db.Column(db.Boolean, default=False)  # Auto-reorder from vendor
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'))
    
    # Relationships
    stock_history = db.relationship('StockHistory', backref='product', lazy=True, cascade='all, delete-orphan')
    stock_batches = db.relationship('StockBatch', backref='product', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_quantity(self):
        """Calculate total quantity from all batches"""
        return sum(batch.quantity for batch in self.stock_batches)
    
    @property
    def threshold_quantity(self):
        """Calculate threshold quantity based on percentage of maximum quantity ever recorded"""
        # Get all historical quantities
        historical_quantities = [h.new_quantity for h in self.stock_history] if self.stock_history else []
        
        # Include current quantity
        all_quantities = historical_quantities + [self.quantity]
        
        # Get the maximum quantity ever recorded
        max_qty = max(all_quantities) if all_quantities else self.quantity
        
        # If max_qty is 0, use a minimum threshold of 5
        if max_qty == 0:
            return 5
        
        # Calculate threshold as percentage of max quantity
        threshold = (max_qty * self.threshold_percentage) / 100
        
        # Ensure minimum threshold of 1
        return max(1, threshold)
    
    @property
    def is_below_threshold(self):
        """Check if current quantity is below threshold"""
        return self.quantity <= self.threshold_quantity
    
    def __repr__(self):
        return f'<Product {self.name}>'

class StockBatch(db.Model):
    """Stock batch model to track individual stock deliveries by date and location"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('warehouse_section.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    arrival_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    batch_number = db.Column(db.String(50))  # Optional batch/lot number
    
    def __repr__(self):
        return f'<StockBatch {self.product_id} - {self.quantity} units>'

class StockHistory(db.Model):
    """Stock history model to track quantity changes"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    old_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    change_reason = db.Column(db.String(200))
    change_type = db.Column(db.String(20))  # 'in', 'out', 'adjustment'
    section_name = db.Column(db.String(100))  # Which section was affected
    date_changed = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    @property
    def quantity_change(self):
        """Calculate the quantity change"""
        return self.new_quantity - self.old_quantity
    
    def __repr__(self):
        return f'<StockHistory {self.product_id}: {self.old_quantity} -> {self.new_quantity}>'

class NotificationLog(db.Model):
    """Log of all notifications sent"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    notification_type = db.Column(db.String(50))  # 'low_stock', 'vendor_alert', etc.
    recipient_email = db.Column(db.String(120))
    recipient_type = db.Column(db.String(20))  # 'manager', 'admin', 'vendor'
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='sent')  # 'sent', 'failed', 'pending'
    sent_date = db.Column(db.DateTime, nullable=False, default=get_ist_time)
    
    def __repr__(self):
        return f'<NotificationLog {self.notification_type} to {self.recipient_email}>'

class SectionCapacityLog(db.Model):
    """Log of section capacity changes (extensions)"""
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('warehouse_section.id'), nullable=False)
    old_capacity = db.Column(db.Integer, nullable=False)
    new_capacity = db.Column(db.Integer, nullable=False)
    change_amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200))  # e.g., "Auto-extended for Product X"
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))  # Which product triggered it
    changed_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Relationships
    section = db.relationship('WarehouseSection', backref='capacity_logs')
    product = db.relationship('Product', backref='capacity_changes')
    
    def __repr__(self):
        return f'<SectionCapacityLog {self.section_id}: {self.old_capacity} -> {self.new_capacity}>'
