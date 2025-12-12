"""
Script to populate all rooms in Det Grønlandske Patienthjem
Run this after creating the migration
"""

from dgp_intra import create_app
from dgp_intra.extensions import db
from dgp_intra.models import Room, CleaningStatus

app = create_app()

def populate_rooms():
    """Create all room entries in the database"""
    
    rooms_to_create = []
    
    # 1st floor: 101-109 (single occupancy)
    for i in range(101, 110):
        rooms_to_create.append({
            'room_number': str(i),
            'floor': 1,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN
        })
    
    # 2nd floor
    # 201-205: Two beds (A and B)
    for i in range(201, 206):
        for suffix in ['A', 'B']:
            rooms_to_create.append({
                'room_number': f'{i}{suffix}',
                'floor': 2,
                'patient_count': 0,
                'relative_count': 0,
                'cleaning_status': CleaningStatus.CLEAN
            })
    
    # 206-217: Single occupancy
    for i in range(206, 218):
        rooms_to_create.append({
            'room_number': str(i),
            'floor': 2,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN
        })
    
    # 3rd floor
    # 301-305: Two beds (A and B)
    for i in range(301, 306):
        for suffix in ['A', 'B']:
            rooms_to_create.append({
                'room_number': f'{i}{suffix}',
                'floor': 3,
                'patient_count': 0,
                'relative_count': 0,
                'cleaning_status': CleaningStatus.CLEAN
            })
    
    # 306-317: Single occupancy
    for i in range(306, 318):
        rooms_to_create.append({
            'room_number': str(i),
            'floor': 3,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN
        })
    
    # 4th floor
    # 401: Two beds (A and B)
    for suffix in ['A', 'B']:
        rooms_to_create.append({
            'room_number': f'401{suffix}',
            'floor': 4,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN
        })
    
    # 402-405: Apartments
    for i in range(402, 406):
        rooms_to_create.append({
            'room_number': str(i),
            'floor': 4,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN,
            'notes': 'Apartment'
        })
    
    # 406-409: Single occupancy
    for i in range(406, 410):
        rooms_to_create.append({
            'room_number': str(i),
            'floor': 4,
            'patient_count': 0,
            'relative_count': 0,
            'cleaning_status': CleaningStatus.CLEAN
        })
    
    with app.app_context():
        # Check if rooms already exist
        existing_count = Room.query.count()
        if existing_count > 0:
            print(f"⚠️  Warning: {existing_count} rooms already exist in database")
            response = input("Do you want to delete all existing rooms and recreate? (yes/no): ")
            if response.lower() == 'yes':
                Room.query.delete()
                db.session.commit()
                print("✅ Deleted existing rooms")
            else:
                print("❌ Aborted")
                return
        
        # Create all rooms
        for room_data in rooms_to_create:
            room = Room(**room_data)
            db.session.add(room)
        
        db.session.commit()
        print(f"✅ Created {len(rooms_to_create)} rooms")
        
        # Summary
        print("\n📊 Room summary:")
        print(f"  Floor 1: {Room.query.filter_by(floor=1).count()} rooms")
        print(f"  Floor 2: {Room.query.filter_by(floor=2).count()} rooms")
        print(f"  Floor 3: {Room.query.filter_by(floor=3).count()} rooms")
        print(f"  Floor 4: {Room.query.filter_by(floor=4).count()} rooms")
        print(f"  Total: {Room.query.count()} rooms")

if __name__ == '__main__':
    populate_rooms()
