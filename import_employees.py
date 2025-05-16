import csv
from werkzeug.security import generate_password_hash
from dgp_intra import create_app
from dgp_intra.extensions import db
from dgp_intra.models import User

app = create_app()

def import_employees(csv_path):
    with app.app_context():
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                name = row['name'].strip()
                email = row['email'].strip()
                is_admin = row['is_admin'].strip().lower() == 'true'
                credit = int(row.get('credit', 0))

                existing = User.query.filter_by(email=email).first()
                if existing:
                    print(f"Skipping existing user: {email}")
                    continue

                user = User(
                    name=name,
                    email=email,
                    is_admin=is_admin,
                    credit=credit,
                    owes=0,
                    password_hash=generate_password_hash("start1234")
                )
                db.session.add(user)
                print(f"Added user: {name} ({email}) — Admin: {is_admin}")

            db.session.commit()
            print("✅ Import complete.")

if __name__ == '__main__':
    import_employees('employees.csv')  # Adjust path if needed