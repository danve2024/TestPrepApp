# WSGI entrypoint
# Allows running with a WSGI server like gunicorn/waitress, while keeping current run.py app

from run import app as application

# If needed to run directly: python wsgi.py
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=True)
