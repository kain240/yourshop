"""
Non-interactive admin bootstrap script for production deployment.
On PythonAnywhere, run this once via the Bash console after setting up the database:

    python create_admin.py

Or pass credentials via environment variables:

    ADMIN_NAME="Shop Owner" ADMIN_EMAIL="admin@example.com" ADMIN_PASSWORD="strongpass123" python create_admin.py
"""
import os
import sys

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app, db
from app.models.user import User, Branch

app = create_app()

with app.app_context():
    print("🔧 YourShop Production Setup")
    print("=" * 40)

    # Create all tables
    print("\n📋 Creating database tables...")
    db.create_all()
    print("✅ Tables created/verified.")

    # Create default branch if none exists
    if Branch.query.count() == 0:
        branch_name = os.environ.get('BRANCH_NAME', 'Main Branch')
        branch_address = os.environ.get('BRANCH_ADDRESS', 'Enter your shop address here')
        branch_phone = os.environ.get('BRANCH_PHONE', '')
        branch = Branch(
            name=branch_name,
            address=branch_address,
            phone=branch_phone,
        )
        db.session.add(branch)
        db.session.flush()
        print(f"✅ Default branch created: '{branch.name}'")
    else:
        branch = Branch.query.first()
        print(f"ℹ️  Using existing branch: '{branch.name}'")

    # Create admin user if none exists
    if User.query.filter_by(role='admin').count() == 0:
        # Try env vars first, then prompt interactively
        name = os.environ.get('ADMIN_NAME', '').strip()
        email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
        password = os.environ.get('ADMIN_PASSWORD', '').strip()

        if not name:
            name = input("Admin name [Admin]: ").strip() or "Admin"
        if not email:
            email = input("Admin email: ").strip().lower()
            if not email:
                print("❌ Email is required.")
                sys.exit(1)
        if not password:
            import getpass
            password = getpass.getpass("Admin password: ").strip()
            if not password:
                print("❌ Password is required.")
                sys.exit(1)

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
        admin = User.query.filter_by(role='admin').first()
        print(f"ℹ️  Admin user already exists: {admin.email}")

    print("\n🚀 Setup complete!")
    print("   Your app is ready to go.")
