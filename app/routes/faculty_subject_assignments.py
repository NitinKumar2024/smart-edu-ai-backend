from flask import Blueprint, request, jsonify
from app.models.db import get_db_connection

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.route('/assigned-subjects', methods=['POST'])
def get_assigned_subjects():
    data = request.get_json()
    if 'faculty_id' not in data or 'college_code' not in data:
        return jsonify({"error": "Missing faculty_id or college_code"}), 400

    faculty_id = data['faculty_id']
    college_code = data['college_code']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch assigned subjects for the faculty
        query_subjects = """
        SELECT sa.assignment_id, s.subject_id, s.subject, s.subject_code
        FROM faculty_subject_assignments sa
        JOIN allsubject s ON sa.subject_id = s.subject_id
        WHERE sa.faculty_id = %s
        """
        cursor.execute(query_subjects, (faculty_id,))
        assigned_subjects = cursor.fetchall()

        subjects = [
            {
                "assignment_id": subject[0],
                "subject_id": subject[1],
                "subject_name": subject[2],
                "subject_code": subject[3]
            }
            for subject in assigned_subjects
        ]

        # Fetch branch details for the faculty's college
        query_branch = """
        SELECT branch_name, branch_code
        FROM branch
        WHERE college_code = %s
        """
        cursor.execute(query_branch, (college_code,))
        branches = cursor.fetchall()

        branch_data = [
            {
                "branch_name": branch[0],
                "branch_code": branch[1]

            }
            for branch in branches
        ]

        return jsonify({
            "message": "Data fetched successfully",
            "data": {
                "assigned_subjects": subjects,
                "branches": branch_data
            }
        }), 200
    except Exception as e:
        return jsonify({"message": "Internal server error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
