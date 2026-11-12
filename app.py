
import os
import uuid

from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from models import User, Expense, Saving, SavingTransaction
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from extensions import db
from permissions import admin_required


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", override=True)


# ==========================================
# 2. INITIALIZE EXTENSIONS
# ==========================================

login_manager = LoginManager()

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        "200 per day",
        "50 per hour"
    ]
)


# ==========================================
# 3. APPLICATION FACTORY
# ==========================================

def create_app():

    app = Flask(__name__)

    # ======================================
    # SECURITY CONFIGURATION
    # ======================================

    secret_key = os.getenv("SECRET_KEY")

    if not secret_key:

        raise RuntimeError(
            "SECRET_KEY is missing from the .env file."
        )

    app.config["SECRET_KEY"] = secret_key

    app.config["SESSION_COOKIE_HTTPONLY"] = True

    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("FLASK_ENV") == "production"
    )

    # ======================================
    # DATABASE CONFIGURATION
    # ======================================

    database_path = BASE_DIR / "umucyo.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{database_path.as_posix()}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ======================================
    # INITIALIZE EXTENSIONS
    # ======================================

    db.init_app(app)

    login_manager.init_app(app)

    csrf.init_app(app)

    limiter.init_app(app)

    # ======================================
    # DATABASE MODELS
    # ======================================

    

    # ======================================
    # CREATE DATABASE TABLES
    # ======================================

    with app.app_context():

        db.create_all()

    # ======================================
    # LOGIN CONFIGURATION
    # ======================================

    login_manager.login_view = "login"

    login_manager.login_message = (
        "Please log in to access UMUCYO Business Manager."
    )

    login_manager.login_message_category = "warning"

    # ======================================
    # LOAD USER FROM DATABASE
    # ======================================

    @login_manager.user_loader
    def load_user(user_id):

        try:

            return db.session.get(
                User,
                int(user_id)
            )

        except (ValueError, TypeError):

            return None

    # ======================================
    # HOME PAGE
    # ======================================

    @app.route("/")
    def index():

        if current_user.is_authenticated:

            return redirect(
                url_for("dashboard")
            )

        return redirect(
            url_for("login")
        )

    # ======================================
    # LOGIN
    # ======================================

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute")
    def login():

        if current_user.is_authenticated:

            return redirect(
                url_for("dashboard")
            )

        if request.method == "POST":

            email = request.form.get(
                "email", ""
            ).strip().lower()

            password = request.form.get(
                "password", ""
            )

            user = User.query.filter_by(
                email=email
            ).first()

            if (
                user
                and user.is_active
                and user.check_password(password)
            ):

                login_user(user)

                flash(
                    "Welcome back, " + user.full_name + "!",
                    "success"
                )

                next_page = request.args.get("next")

                if (
                    next_page
                    and next_page.startswith("/")
                    and not next_page.startswith("//")
                ):

                    return redirect(next_page)

                return redirect(
                    url_for("dashboard")
                )

            flash(
                "Invalid email or password, or account inactive.",
                "danger"
            )

        return render_template("login.html")

    # ======================================
    # DASHBOARD
    # ======================================

    @app.route("/dashboard")
    @login_required
    def dashboard():

        return render_template(
            "dashboard.html"
        )

    # ======================================
    # EXPENSE SUBMISSION
    # ======================================

    @app.route(
        "/expenses/new",
        methods=["GET", "POST"]
    )
    @login_required
    def create_expense():

        if request.method == "POST":

            category = request.form.get(
                "category", ""
            ).strip()

            description = request.form.get(
                "description", ""
            ).strip()

            supplier = request.form.get(
                "supplier", ""
            ).strip()

            expense_date_text = request.form.get(
                "expense_date", ""
            ).strip()

            amount_text = request.form.get(
                "amount", ""
            ).strip()

            payment_method = request.form.get(
                "payment_method", ""
            ).strip()

            reference = request.form.get(
                "reference", ""
            ).strip()

            # VALIDATE REQUIRED FIELDS

            if not all([
                category,
                description,
                expense_date_text,
                amount_text,
                payment_method
            ]):

                flash(
                    "Please complete all required fields.",
                    "danger"
                )

                return render_template(
                    "new_expense.html"
                )

            # VALIDATE DATE AND AMOUNT

            try:

                expense_date = datetime.strptime(
                    expense_date_text,
                    "%Y-%m-%d"
                ).date()

                amount = Decimal(amount_text)

                if not amount.is_finite() or amount <= 0:

                    raise ValueError(
                        "Invalid amount"
                    )

            except (ValueError, InvalidOperation):

                flash(
                    "Enter a valid date and positive expense amount.",
                    "danger"
                )

                return render_template(
                    "new_expense.html"
                )

            # CREATE EXPENSE RECORD

            expense = Expense(

                expense_id=(
                    "EXP-" +
                    uuid.uuid4().hex[:10].upper()
                ),

                expense_date=expense_date,

                category=category,

                description=description,

                supplier=supplier or None,

                amount=amount,

                payment_method=payment_method,

                reference=reference or None,

                recorded_by_id=current_user.id,

                status="pending"
            )

            try:

                db.session.add(expense)

                db.session.commit()

                flash(
                    f"Expense {expense.expense_id} submitted successfully. "
                    "It is awaiting administrator approval.",
                    "success"
                )

                return redirect(
                    url_for("create_expense")
                )

            except Exception:

                db.session.rollback()

                app.logger.exception(
                    "EXPENSE SUBMISSION FAILED"
                )

                flash(
                    "Could not save the expense. Please try again.",
                    "danger"
                )

        return render_template(
            "new_expense.html"
        )

    # ======================================
    # EXPENSE MANAGEMENT
    # ======================================

    @app.route("/expenses")
    @admin_required
    def expense_management():

        expenses = Expense.query.order_by(
            Expense.created_at.desc()
        ).all()

        users = User.query.all()

        user_names = {
            user.id: user.full_name
            for user in users
        }

        return render_template(
            "expenses.html",
            expenses=expenses,
            user_names=user_names
        )

    # ======================================
    # APPROVE EXPENSE
    # ======================================

    @app.route(
        "/expenses/<int:expense_id>/approve",
        methods=["POST"]
    )
    @admin_required
    def approve_expense(expense_id):

        expense = Expense.query.get_or_404(
            expense_id
        )

        # ONLY PENDING EXPENSES CAN BE APPROVED

        if expense.status != "pending":

            flash(
                "This expense has already been processed.",
                "warning"
            )

            return redirect(
                url_for("expense_management")
            )

        try:

            # UPDATE EXPENSE STATUS

            expense.status = "approved"

            # RECORD APPROVING ADMINISTRATOR

            expense.approved_by_id = current_user.id

            # RECORD APPROVAL DATE AND TIME

            expense.approved_at = datetime.now(
                timezone.utc
            )

            db.session.commit()

            flash(
                f"Expense {expense.expense_id} approved successfully.",
                "success"
            )

        except Exception:

            db.session.rollback()

            app.logger.exception(
                "EXPENSE APPROVAL FAILED"
            )

            flash(
                "Unable to approve this expense. Please try again.",
                "danger"
            )

        return redirect(
            url_for("expense_management")
        )

    # ======================================
    # CREATE STAFF ACCOUNT
    # ======================================

    @app.route(
        "/users/create",
        methods=["GET", "POST"]
    )
    @admin_required
    def create_staff():

        if request.method == "POST":

            full_name = request.form.get(
                "full_name", ""
            ).strip()

            email = request.form.get(
                "email", ""
            ).strip().lower()

            password = request.form.get(
                "password", ""
            )

            confirm_password = request.form.get(
                "confirm_password", ""
            )

            if not full_name or not email:

                flash(
                    "Name and email are required.",
                    "danger"
                )

                return render_template(
                    "create_staff.html"
                )

            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:

                flash(
                    "This email is already registered.",
                    "danger"
                )

                return render_template(
                    "create_staff.html"
                )

            if len(password) < 12:

                flash(
                    "Password must contain at least 12 characters.",
                    "danger"
                )

                return render_template(
                    "create_staff.html"
                )

            if password != confirm_password:

                flash(
                    "Passwords do not match.",
                    "danger"
                )

                return render_template(
                    "create_staff.html"
                )

            staff = User(

                full_name=full_name,

                email=email,

                role="staff",

                is_active=True
            )

            staff.set_password(password)

            try:

                db.session.add(staff)

                db.session.commit()

                app.logger.info(
                    "Staff account created: %s",
                    email
                )

                flash(
                    "Staff account created successfully.",
                    "success"
                )

                return redirect(
                    url_for("create_staff")
                )

            except Exception:

                db.session.rollback()

                app.logger.exception(
                    "STAFF ACCOUNT CREATION FAILED"
                )

                flash(
                    "Could not create the staff account. "
                    "Check the server log for details.",
                    "danger"
                )

        return render_template(
            "create_staff.html"
        )

    # ======================================
    # STAFF DIRECTORY
    # ======================================

    @app.route("/users")
    @admin_required
    def staff_directory():

        search_query = request.args.get(
            "q", ""
        ).strip()

        staff_query = User.query.filter_by(
            role="staff"
        )

        # SEARCH BY NAME OR EMAIL

        if search_query:

            search_term = f"%{search_query}%"

            staff_query = staff_query.filter(
                db.or_(
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )

        staff_members = staff_query.order_by(
            User.created_at.desc()
        ).all()

        total_staff = User.query.filter_by(
            role="staff"
        ).count()

        active_staff = User.query.filter_by(
            role="staff",
            is_active=True
        ).count()

        inactive_staff = User.query.filter_by(
            role="staff",
            is_active=False
        ).count()

        return render_template(
            "users.html",
            staff_members=staff_members,
            search_query=search_query,
            total_staff=total_staff,
            active_staff=active_staff,
            inactive_staff=inactive_staff
        )

    # ======================================
    # ACTIVATE / DEACTIVATE STAFF
    # ======================================

    @app.route(
        "/users/<int:user_id>/toggle-status",
        methods=["POST"]
    )
    @admin_required
    def toggle_staff_status(user_id):

        staff = db.session.get(
            User,
            user_id
        )

        if staff is None:

            abort(404)

        # ONLY STAFF ACCOUNTS CAN BE CHANGED

        if staff.role != "staff":

            abort(403)

        # CHANGE ACCOUNT STATUS

        staff.is_active = not staff.is_active

        try:

            db.session.commit()

            if staff.is_active:

                flash(
                    f"{staff.full_name}'s account has been activated.",
                    "success"
                )

            else:

                flash(
                    f"{staff.full_name}'s account has been deactivated.",
                    "warning"
                )

            app.logger.info(
                "Administrator %s changed staff %s status to %s",
                current_user.id,
                staff.id,
                "active" if staff.is_active else "inactive"
            )

        except Exception:

            db.session.rollback()

            app.logger.exception(
                "STAFF STATUS UPDATE FAILED"
            )

            flash(
                "Could not update the staff account status.",
                "danger"
            )

        return redirect(
            url_for(
                "staff_directory",
                q=request.form.get("q", "")
            )
        )

    
    # ======================================
    # SAVINGS OVERVIEW
    # ======================================

    @app.route("/savings")
    @admin_required
    def savings_overview():

        savings = Saving.query.order_by(
            Saving.created_at.desc()
        ).all()

        total_target = sum(
            (Decimal(str(s.target_amount)) for s in savings),
            Decimal("0.00")
        )

        total_balance = sum(
            (s.current_balance for s in savings),
            Decimal("0.00")
        )

        total_remaining = sum(
            (s.remaining_amount for s in savings),
            Decimal("0.00")
        )

        return render_template(
            "savings.html",
            savings=savings,
            total_target=total_target,
            total_balance=total_balance,
            total_remaining=total_remaining
        )


    # ======================================
    # CREATE SAVINGS ACCOUNT
    # ======================================

    @app.route(
        "/savings/new",
        methods=["GET", "POST"]
    )
    @admin_required
    def create_saving():

        if request.method == "POST":

            saving_name = request.form.get(
                "saving_name", ""
            ).strip()

            target_amount_text = request.form.get(
                "target_amount", ""
            ).strip()

            start_date_text = request.form.get(
                "start_date", ""
            ).strip()

            target_date_text = request.form.get(
                "target_date", ""
            ).strip()

            notes = request.form.get(
                "notes", ""
            ).strip()

            if not saving_name or not target_amount_text or not start_date_text:

                flash(
                    "Complete the savings name, target amount and start date.",
                    "danger"
                )

                return render_template("create_saving.html")

            try:

                target_amount = Decimal(target_amount_text)

                start_date = datetime.strptime(
                    start_date_text,
                    "%Y-%m-%d"
                ).date()

                target_date = None

                if target_date_text:

                    target_date = datetime.strptime(
                        target_date_text,
                        "%Y-%m-%d"
                    ).date()

                if not target_amount.is_finite() or target_amount <= 0:
                    raise ValueError("Invalid target")

                if target_date and target_date < start_date:
                    raise ValueError("Invalid target date")

            except (ValueError, InvalidOperation):

                flash(
                    "Enter a valid target amount and dates. "
                    "The target date cannot be before the start date.",
                    "danger"
                )

                return render_template("create_saving.html")

            saving = Saving(

                saving_id="SAV-" + uuid.uuid4().hex[:10].upper(),

                saving_name=saving_name,

                target_amount=target_amount,

                start_date=start_date,

                target_date=target_date,

                status="active",

                notes=notes or None,

                created_by_id=current_user.id
            )

            try:

                db.session.add(saving)

                db.session.commit()

                flash(
                    f"Savings goal {saving.saving_name} created successfully.",
                    "success"
                )

                return redirect(url_for("savings_overview"))

            except Exception:

                db.session.rollback()

                app.logger.exception("SAVINGS CREATION FAILED")

                flash(
                    "Could not create the savings account.",
                    "danger"
                )

        return render_template("create_saving.html")


    # ======================================
    # RECORD SAVINGS DEPOSIT / WITHDRAWAL
    # ======================================

    @app.route(
        "/savings/<int:saving_id>/transaction",
        methods=["GET", "POST"]
    )
    @admin_required
    def saving_transaction(saving_id):

        saving = Saving.query.get_or_404(saving_id)

        if request.method == "POST":

            transaction_type = request.form.get(
                "transaction_type", ""
            ).strip().lower()

            amount_text = request.form.get(
                "amount", ""
            ).strip()

            transaction_date_text = request.form.get(
                "transaction_date", ""
            ).strip()

            payment_method = request.form.get(
                "payment_method", ""
            ).strip()

            reference = request.form.get(
                "reference", ""
            ).strip()

            notes = request.form.get(
                "notes", ""
            ).strip()

            if transaction_type not in ("deposit", "withdrawal"):

                flash(
                    "Select a valid transaction type.",
                    "danger"
                )

                return render_template(
                    "savings_transaction.html",
                    saving=saving
                )

            if not all([
                amount_text,
                transaction_date_text,
                payment_method
            ]):

                flash(
                    "Complete all required transaction fields.",
                    "danger"
                )

                return render_template(
                    "savings_transaction.html",
                    saving=saving
                )

            try:

                amount = Decimal(amount_text)

                transaction_date = datetime.strptime(
                    transaction_date_text,
                    "%Y-%m-%d"
                ).date()

                if not amount.is_finite() or amount <= 0:
                    raise ValueError("Invalid amount")

            except (ValueError, InvalidOperation):

                flash(
                    "Enter a valid transaction amount and date.",
                    "danger"
                )

                return render_template(
                    "savings_transaction.html",
                    saving=saving
                )

            if saving.status == "paused":

                flash(
                    "This savings account is paused. Resume it before recording transactions.",
                    "warning"
                )

                return redirect(url_for("savings_overview"))

            if (
                transaction_type == "withdrawal"
                and amount > saving.current_balance
            ):

                flash(
                    "Insufficient savings balance. "
                    f"Available balance: {saving.current_balance:,.2f}",
                    "danger"
                )

                return render_template(
                    "savings_transaction.html",
                    saving=saving
                )

            transaction = SavingTransaction(

                transaction_id="STX-" + uuid.uuid4().hex[:10].upper(),

                saving_id=saving.id,

                transaction_date=transaction_date,

                transaction_type=transaction_type,

                amount=amount,

                payment_method=payment_method,

                reference=reference or None,

                notes=notes or None,

                recorded_by_id=current_user.id
            )

            try:

                db.session.add(transaction)

                db.session.commit()

                flash(
                    f"{transaction_type.title()} recorded successfully.",
                    "success"
                )

                return redirect(url_for("savings_overview"))

            except Exception:

                db.session.rollback()

                app.logger.exception(
                    "SAVINGS TRANSACTION FAILED"
                )

                flash(
                    "Could not save this transaction.",
                    "danger"
                )

        return render_template(
            "savings_transaction.html",
            saving=saving
        )


    # ======================================
    # SAVINGS TRANSACTION HISTORY
    # ======================================

    @app.route("/savings/<int:saving_id>/history")
    @admin_required
    def saving_history(saving_id):

        saving = Saving.query.get_or_404(saving_id)

        transactions = SavingTransaction.query.filter_by(
            saving_id=saving.id
        ).order_by(
            SavingTransaction.transaction_date.desc(),
            SavingTransaction.created_at.desc()
        ).all()

        user_ids = {
            transaction.recorded_by_id
            for transaction in transactions
        }

        users = User.query.filter(
            User.id.in_(user_ids)
        ).all() if user_ids else []

        user_names = {
            user.id: user.full_name
            for user in users
        }

        return render_template(
            "savings_history.html",
            saving=saving,
            transactions=transactions,
            user_names=user_names
        )


    # ======================================
    # PAUSE / RESUME SAVINGS
    # ======================================

    @app.route(
        "/savings/<int:saving_id>/toggle-status",
        methods=["POST"]
    )
    @admin_required
    def toggle_saving_status(saving_id):

        saving = Saving.query.get_or_404(saving_id)

        if saving.status == "active":
            saving.status = "paused"
            message = "Savings account paused."
        else:
            saving.status = "active"
            message = "Savings account resumed."

        try:

            db.session.commit()

            flash(message, "success")

        except Exception:

            db.session.rollback()

            app.logger.exception(
                "SAVINGS STATUS UPDATE FAILED"
            )

            flash(
                "Could not update the savings account status.",
                "danger"
            )

        return redirect(url_for("savings_overview"))

    # ======================================
    # LOGOUT
    # ======================================

    @app.route(
        "/logout",
        methods=["POST"]
    )
    @login_required
    def logout():

        logout_user()

        flash(
            "You have logged out successfully.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    # ======================================
    # HEALTH CHECK
    # ======================================

    @app.route("/health")
    def health():

        return {
            "application": "UMUCYO Business Manager",
            "status": "running"
        }, 200

    # ======================================
    # RETURN APPLICATION
    # ======================================

    return app


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

app = create_app()


if __name__ == "__main__":

    app.run(debug=True)
