from data import users
from datetime import date
from flask import session

def get_user_id_and_hash(username):
    """Retrieves UserID and PasswordHash from login_info.db using the Username."""
    cols, rows = users.execute_sql(
        users.LOGIN_KEY,
        "SELECT UserID, PasswordHash FROM logins WHERE Username = ?",
        (username,)
    )
    if rows:
        # Returns (UserID, PasswordHash)
        return rows[0]
    return None


def get_user_data_by_id(user_id):
    """Retrieves FirstName and Email from users_data.db using the UserID."""
    cols, rows = users.execute_sql(
        users.USERS_KEY,
        "SELECT FirstName, Email FROM users WHERE UserID = ?",
        (user_id,)
    )
    if rows:
        # Returns (FirstName, Email)
        return rows[0]
    return None, None


def login_required(f):
    """Decorator to ensure a user is logged in before accessing a route."""
    from functools import wraps
    from flask import redirect, url_for, flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in(session):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_logged_in(session):
    """Checks if a user is authenticated via session and refreshes session data."""
    if 'user_id' in session:
        # Get the username from the session if it exists
        current_username = session.get('username')
        if not current_username:
            return False
            
        # Verify the user exists and matches the session
        user_data = get_user_data_by_id(session['user_id'])
        if not user_data or len(user_data) < 2:
            return False
            
        first_name, email = user_data
        
        # Get the username from the database for this user_id
        cols, rows = users.execute_sql(
            users.LOGIN_KEY,
            "SELECT Username FROM logins WHERE UserID = ?",
            (session['user_id'],)
        )
        
        if not rows or not rows[0] or rows[0][0] != current_username:
            return False
            
        # Update session data
        if first_name:
            session['first_name'] = first_name
        if email:
            session['email'] = email
            
        return True
    return False


def get_today_date():
    """Get today's date in YYYY-MM-DD format."""
    return date.today().isoformat()