from app import db
from datetime import datetime

class Product(db.Model):
    """Product model for inventory items"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(100), nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to stock history
    stock_history = db.relationship('StockHistory', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Product {self.name}>'

class StockHistory(db.Model):
    """Stock history model to track quantity changes"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    old_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    change_reason = db.Column(db.String(200))
    date_changed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    @property
    def quantity_change(self):
        """Calculate the quantity change"""
        return self.new_quantity - self.old_quantity
    
    def __repr__(self):
        return f'<StockHistory {self.product_id}: {self.old_quantity} -> {self.new_quantity}>'
