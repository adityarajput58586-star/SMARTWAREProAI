"""
SmartWare Pro - Database Status Checker
Run this to see what's in your database
"""

from app import app, db
from models import Product, AuthorizedUser, Vendor, WarehouseSection, StockBatch, StockHistory
import os

def check_database():
    print("=" * 60)
    print("SmartWare Pro - Database Status")
    print("=" * 60)
    print()
    
    # Check if database file exists
    db_path = "instance/warehouse.db"
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"✅ Database file exists: {db_path}")
        print(f"   Size: {size:,} bytes ({size/1024:.2f} KB)")
    else:
        print(f"❌ Database file NOT found: {db_path}")
        print("   The database will be created when you run the app.")
        return
    
    print()
    print("-" * 60)
    print("Database Contents:")
    print("-" * 60)
    
    with app.app_context():
        # Count records in each table
        tables = [
            ("Products", Product),
            ("Authorized Users", AuthorizedUser),
            ("Vendors", Vendor),
            ("Warehouse Sections", WarehouseSection),
            ("Stock Batches", StockBatch),
            ("Stock History", StockHistory),
        ]
        
        total_records = 0
        for name, model in tables:
            try:
                count = model.query.count()
                total_records += count
                status = "✅" if count > 0 else "⚠️"
                print(f"{status} {name:.<30} {count:>5} records")
            except Exception as e:
                print(f"❌ {name:.<30} Error: {str(e)}")
        
        print("-" * 60)
        print(f"Total Records: {total_records}")
        print()
        
        # Show some sample data
        if Product.query.count() > 0:
            print("Sample Products:")
            products = Product.query.limit(5).all()
            for p in products:
                print(f"  • {p.name} - Qty: {p.quantity} - Location: {p.location}")
            print()
        
        if AuthorizedUser.query.count() > 0:
            print("Authorized Users:")
            users = AuthorizedUser.query.all()
            for u in users:
                status = "Active" if u.is_active else "Inactive"
                print(f"  • {u.name} ({u.email}) - {u.role} - {status}")
            print()
        
        if WarehouseSection.query.count() > 0:
            print("Warehouse Sections:")
            sections = WarehouseSection.query.all()
            for s in sections:
                usage = f"{s.current_usage}/{s.capacity}"
                print(f"  • {s.name} - {usage} units ({s.usage_percentage:.1f}% full)")
            print()
    
    print("=" * 60)
    print("Database check complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        check_database()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the app is not running when checking the database.")
    
    input("\nPress Enter to exit...")
