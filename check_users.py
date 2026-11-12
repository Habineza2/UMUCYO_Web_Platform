
from app import create_app
from models import User

app = create_app()

with app.app_context():

    users = User.query.all()

    print("\n===== UMUCYO REGISTERED USERS =====")
    print("Total users:", len(users))

    for user in users:
        print("------------------------------")
        print("ID:", user.id)
        print("Name:", user.full_name)
        print("Email:", user.email)
        print("Role:", user.role)
        print("Active:", user.is_active)
        print("Password hash exists:", bool(user.password_hash))

    if not users:
        print("No users found in this database.")
