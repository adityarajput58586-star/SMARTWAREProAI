"""
Clean up test data from database
"""
from app import app, db
from models import Product, StockBatch
from utils import update_section_usage

def cleanup():
    """Remove test products and update section usage"""
    with app.app_context():
        print("\n🧹 Cleaning up test data...")
        
        # Find and delete test products
        test_products = Product.query.filter(Product.name.like('Test Product%')).all()
        
        for product in test_products:
            print(f"   Deleting: {product.name} ({product.quantity} {product.unit_type})")
            # Delete associated batches
            StockBatch.query.filter_by(product_id=product.id).delete()
            # Delete product
            db.session.delete(product)
        
        db.session.commit()
        
        # Update section usage
        update_section_usage(db)
        
        print(f"✅ Cleanup complete!\n")

if __name__ == '__main__':
    cleanup()
