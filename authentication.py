from data import users
from datetime import date

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
    return None, None


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


def is_logged_in(session):
    """Checks if a user is authenticated via session and refreshes session data."""
    if 'user_id' in session:
        # Refresh user data on page load for dynamic display
        first_name, email = get_user_data_by_id(session['user_id'])
        if first_name:
            session['first_name'] = first_name
            return True
    return False


def get_today_date():
    """Get today's date in YYYY-MM-DD format."""
    return date.today().isoformat()