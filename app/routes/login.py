from flask import Blueprint, request, jsonify
from app.models.db import get_db_connection
import bcrypt

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing email or password"}), 400

    email = data['email']
    password = data['password']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch the user based on email
        query = "SELECT username, email, number, password, college_code, unique_token FROM faculty WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user:
            hashed_password = user[3]  # Password hash stored in the database

            # Verify the provided password against the stored hash
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                return jsonify({
                    "message": "Login successful",
                    "user": {
                        "username": user[0],
                        "email": user[1],
                        "number": user[2],
                        "college_code": user[4],
                        "unique_token": user[5]
                    }
                }), 200
            else:
                return jsonify({"error": "Invalid password"}), 401
        else:
            return jsonify({"error": "Invalid email"}), 401
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
