"""
YourShop Database Setup Script
Run this ONCE after configuring your .env to create the database and admin user.
Usage: python setup.py
"""
import os
import sys

# Load env first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("ERROR: python-dotenv not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from app import create_app, db
from app.models.user import User, Branch

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("✅ Tables created.")

    # Check if any branch exists
    if Branch.query.count() == 0:
        branch = Branch(
            name="Main Branch",
            address="Enter your shop address here",
            phone="",
        )
        db.session.add(branch)
        db.session.flush()
        print(f"✅ Default branch created: '{branch.name}'")
    else:
        branch = Branch.query.first()
        print(f"ℹ️  Using existing branch: '{branch.name}'")

    # Check if admin exists
    if User.query.filter_by(role='admin').count() == 0:
        print("\n--- Create Admin User ---")
        name = input("Admin name: ").strip() or "Admin"
        email = input("Admin email: ").strip().lower()
        password = input("Admin password: ").strip()

        admin = User(
            name=name,
            email=email,
            role='admin',
            branch_id=branch.id
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"\n✅ Admin user '{name}' ({email}) created!")
    else:
        db.session.commit()
        print("ℹ️  Admin user already exists.")

    print("\n🚀 Setup complete! Run: python run.py")
    print("   Then open: http://localhost:5000/login")
