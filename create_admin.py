
from getpass import getpass

from app import create_app, db
from models import User


app = create_app()


def create_administrator():

    with app.app_context():

        # Check whether an administrator already exists
        existing_admin = User.query.filter_by(
            role="administrator"
        ).first()

        if existing_admin:
            print("An administrator account already exists.")
            return

        print("\n================================")
        print(" UMUCYO ADMINISTRATOR SETUP")
        print("================================\n")

        full_name = input("Administrator full name: ").strip()

        email = input("Administrator email: ").strip().lower()

        if not full_name or not email:
            print("Name and email are required.")
            return

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            print("This email address is already registered.")
            return

        password = getpass("Create password: ")

        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match.")
            return

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
            return

        # Create administrator
        administrator = User(
            full_name=full_name,
            email=email,
            role="administrator",
            is_active=True
        )

        administrator.set_password(password)

        try:
            db.session.add(administrator)
            db.session.commit()

            print("\nAdministrator created successfully!")
            print("Name:", administrator.full_name)
            print("Email:", administrator.email)
            print("Role:", administrator.role)

        except Exception as error:
            db.session.rollback()
            print("Could not create administrator:", error)


if __name__ == "__main__":
    create_administrator()
