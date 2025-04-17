# run.py
# This script imports the app factory and runs the app.
from app import create_app

# Call the factory to create the app instance
app = create_app()

if __name__ == '__main__':
    # Run the app using the instance created by the factory
    # Port 5001, debug=True for development
    app.run(debug=True, port=5001)