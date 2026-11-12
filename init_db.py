
from app import create_app, db
import models

app = create_app()

with app.app_context():

    db.create_all()

    print("UMUCYO database created successfully.")

    print("User table created successfully.")
