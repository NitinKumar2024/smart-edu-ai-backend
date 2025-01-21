from flask import Blueprint, request, jsonify
from app.models.db import get_db_connection

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('/subjects', methods=['GET'])
def get_subjects():
    try:
        # Get token from header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is required'}), 401

        # Remove 'Bearer ' if present
        token = token.replace('Bearer ', '')

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()

        # First validate token and get student details
        cursor.execute("""
            SELECT branch, semester, college_code 
            FROM students 
            WHERE unique_token = %s
        """, (token,))

        student = cursor.fetchone()
        if not student:
            return jsonify({'error': 'Invalid token'}), 401

        branch_code, semester, college_code = student

        # Get subjects for the student's branch, semester and college
        cursor.execute("""
            SELECT subject_id, Subject 
            FROM allsubject 
            WHERE branch_code = %s 
            AND semester = %s 
            AND college_code = %s
        """, (branch_code, semester, college_code))

        subjects = cursor.fetchall()

        # Format response
        subjects_list = [
            {
                'subject_id': subject[0],
                'subject_name': subject[1]
            }
            for subject in subjects
        ]

        cursor.close()
        conn.close()

        return jsonify({
            'message': 'success',
            'data': subjects_list
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500