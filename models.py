
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from extensions import db


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(120), nullable=False)

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(
        db.String(30),
        nullable=False,
        default="staff"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_administrator(self):
        return self.role == "administrator"

    def __repr__(self):
        return f"<User {self.email}>"


class Expense(db.Model):

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)

    expense_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    expense_date = db.Column(db.Date, nullable=False)

    category = db.Column(db.String(100), nullable=False)

    description = db.Column(db.Text, nullable=False)

    supplier = db.Column(db.String(150))

    amount = db.Column(db.Numeric(12, 2), nullable=False)

    payment_method = db.Column(db.String(50), nullable=False)

    reference = db.Column(db.String(100))

    recorded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    approved_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    decision_note = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


# ==========================================
# SAVINGS ACCOUNTS
# ==========================================

class Saving(db.Model):

    __tablename__ = "savings"

    id = db.Column(db.Integer, primary_key=True)

    saving_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    saving_name = db.Column(
        db.String(150),
        nullable=False
    )

    target_amount = db.Column(
        db.Numeric(14, 2),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    target_date = db.Column(
        db.Date,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )

    notes = db.Column(db.Text, nullable=True)

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    transactions = db.relationship(
        "SavingTransaction",
        backref="saving",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="SavingTransaction.transaction_date.desc()"
    )

    @property
    def current_balance(self):

        from decimal import Decimal

        balance = Decimal("0.00")

        for transaction in self.transactions:

            if transaction.transaction_type == "deposit":
                balance += transaction.amount

            elif transaction.transaction_type == "withdrawal":
                balance -= transaction.amount

        return balance

    @property
    def remaining_amount(self):

        from decimal import Decimal

        remaining = (
            Decimal(self.target_amount)
            - self.current_balance
        )

        return max(remaining, Decimal("0.00"))

    @property
    def progress_percentage(self):

        from decimal import Decimal

        target = Decimal(self.target_amount)

        if target <= 0:
            return Decimal("0.00")

        percentage = (
            self.current_balance / target
        ) * Decimal("100")

        return min(percentage, Decimal("100.00"))

    @property
    def display_status(self):

        if self.status == "paused":
            return "Paused"

        if self.current_balance >= self.target_amount:
            return "Completed"

        return "Active"


# ==========================================
# SAVINGS TRANSACTIONS
# ==========================================

class SavingTransaction(db.Model):

    __tablename__ = "saving_transactions"

    id = db.Column(db.Integer, primary_key=True)

    transaction_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    saving_id = db.Column(
        db.Integer,
        db.ForeignKey("savings.id"),
        nullable=False,
        index=True
    )

    transaction_date = db.Column(
        db.Date,
        nullable=False
    )

    transaction_type = db.Column(
        db.String(20),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(14, 2),
        nullable=False
    )

    payment_method = db.Column(
        db.String(50),
        nullable=False
    )

    reference = db.Column(
        db.String(100),
        nullable=True
    )

    notes = db.Column(
        db.Text,
        nullable=True
    )

    recorded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
