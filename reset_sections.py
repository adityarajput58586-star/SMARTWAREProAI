"""
Reset warehouse sections to original capacities
"""
from app import app, db
from models import WarehouseSection, SectionCapacityLog

def reset_sections():
    """Reset all sections to their original capacities"""
    with app.app_context():
        print("\n🔄 Resetting warehouse sections to original capacities...")
        
        # Original capacities
        original_capacities = {
            "Section A": 200,
            "Section B": 200,
            "Section C": 150,
            "Section D": 150,
            "Section E": 100
        }
        
        sections = WarehouseSection.query.all()
        
        for section in sections:
            if section.name in original_capacities:
                original = original_capacities[section.name]
                current = section.capacity
                
                if current != original:
                    print(f"   {section.name}: {current} → {original}")
                    
                    # Check if we can safely reduce capacity
                    if section.current_usage > original:
                        print(f"      ⚠️  Cannot reset: Current usage ({section.current_usage}) exceeds original capacity ({original})")
                        print(f"      💡 Remove stock first or keep extended capacity")
                    else:
                        section.capacity = original
                        print(f"      ✅ Reset successful")
                else:
                    print(f"   {section.name}: Already at original capacity ({original})")
        
        db.session.commit()
        print(f"\n✅ Section reset complete!\n")

if __name__ == '__main__':
    reset_sections()
