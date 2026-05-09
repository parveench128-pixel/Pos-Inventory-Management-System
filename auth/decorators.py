from functools import wraps
from flask import redirect, url_for, session

from db import db
from models import User , ActivityLog


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def management_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role not in ('admin', 'manager'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'manager':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ACTIVITY LOG HELPER ====================


def log_activity(user_id, action, description=''):
    """Call this to record any cashier/user action for manager monitoring."""
    try:
        log = ActivityLog(user_id=user_id, action=action,
                          description=description)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
