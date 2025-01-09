import datetime
import random
import string

import requests
from flask import Blueprint, request, jsonify

from app.models.db import get_db_connection

forgot_email_bp = Blueprint('forgot_email', __name__)

@forgot_email_bp.route('/forgot_email', methods=['POST'])
def forgot_email():
    data = request.get_json()
    if 'email' not in data or 'role' not in data:
        return jsonify({"error": "Email or role parameter is missing"}), 400

    email = data['email']
    role = data['role']

    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the email exists in the specified role table
        cursor.execute(f"SELECT password FROM `{role}` WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "No records found for the provided email"}), 404

        # Generate a unique token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=64))

        # Calculate expiration date (15 minutes from now)
        expire_date = (datetime.datetime.now() + datetime.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')

        # Check if there's an existing token for the user's email
        cursor.execute("SELECT * FROM reset_tokens WHERE email = %s", (email,))
        existing_token = cursor.fetchone()

        if existing_token:
            # Update the existing token record
            cursor.execute(
                "UPDATE reset_tokens SET token = %s, expire_date = %s WHERE email = %s",
                (token, expire_date, email)
            )
        else:
            # Insert a new token record
            cursor.execute(
                "INSERT INTO reset_tokens (email, token, expire_date) VALUES (%s, %s, %s)",
                (email, token, expire_date)
            )

        # Commit the transaction
        conn.commit()

        # Generate the reset link
        reset_link = f"https://helper-smartedu.turbocampuspro.com/auth/reset_password.php?token={token}&email={email}&role={role}"

        # Send the reset link via an external email API
        email_data = {
            'to': email,
            'resetLink': reset_link
        }
        email_api_url = 'https://service.insidemark.in/smartedu/forgot_email.php'
        response = requests.post(email_api_url, data=email_data)

        if response.status_code != 200:
            return jsonify({"error": "Failed to send reset email"}), 500

        return jsonify({
            "message": "Password reset link sent successfully",
            "resetLink": reset_link
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
