
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(function):

    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):

        if not current_user.is_administrator:
            abort(403)

        return function(*args, **kwargs)

    return decorated_function
