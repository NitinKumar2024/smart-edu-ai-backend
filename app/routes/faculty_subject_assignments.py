from flask import Blueprint, request, jsonify
from app.models.db import get_db_connection

faculty_bp = Blueprint('faculty', __name__)

class TokenValidator:
    @staticmethod
    def validate_token(auth_header):
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, {"error": "Missing or invalid Authorization header"}

        token = auth_header.split(' ')[1]

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = """
            SELECT faculty_id, college_code
            FROM faculty
            WHERE unique_token = %s
            """
            cursor.execute(query, (token,))
            faculty = cursor.fetchone()

            if not faculty:
                return None, {"error": "Invalid token"}

            return {
                "faculty_id": faculty[0],
                "college_code": faculty[1]
            }, None
        except Exception as e:
            return None, {"error": "Internal server error", "details": str(e)}
        finally:
            cursor.close()
            conn.close()

@faculty_bp.route('/assigned-subjects', methods=['GET'])
def get_assigned_subjects():
    auth_header = request.headers.get('Authorization')
    faculty_data, error = TokenValidator.validate_token(auth_header)

    if error:
        return jsonify(error), 400 if "error" in error and error["error"] == "Invalid token" else 500

    faculty_id = faculty_data['faculty_id']
    branch_code = request.args.get('branch_code')
    semester = request.args.get('semester')
    college_code = faculty_data['college_code']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch assigned subjects for the faculty
        query_subjects = """
        SELECT sa.assignment_id, s.subject_id, s.subject, s.subject_code
        FROM faculty_subject_assignments sa
        JOIN allsubject s ON sa.subject_id = s.subject_id
        WHERE sa.faculty_id = %s AND s.branch_code = %s AND s.semester = %s
        """
        cursor.execute(query_subjects, (faculty_id, branch_code, semester,))
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


        return jsonify({
            "message": "Data fetched successfully",
            "data": {
                "assigned_subjects": subjects

            }
        }), 200
    except Exception as e:
        return jsonify({"message": "Internal server error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@faculty_bp.route('/branch-details', methods=['GET'])
def get_branch_details():
    auth_header = request.headers.get('Authorization')
    faculty_data, error = TokenValidator.validate_token(auth_header)

    if error:
        return jsonify(error), 400 if "error" in error and error["error"] == "Invalid token" else 500

    faculty_id = faculty_data['faculty_id']
    college_code = faculty_data['college_code']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

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
                "branches": branch_data
            }
        }), 200
    except Exception as e:
        return jsonify({"message": "Internal server error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
@faculty_bp.route('/subject-details', methods=['GET'])
def get_subject_details():
    subject_id = request.args.get('subject_id')

    if not subject_id:
        return jsonify({"error": "Missing subject_id parameter"}), 400

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch chapters for the given subject_id
        query_chapters = """
        SELECT chapter_id, chapter_name
        FROM chapters
        WHERE subject_id = %s
        """
        cursor.execute(query_chapters, (subject_id,))
        chapters = cursor.fetchall()

        chapter_data = []

        for chapter in chapters:
            chapter_id = chapter[0]
            chapter_name = chapter[1]

            # Fetch topics for each chapter
            query_topics = """
            SELECT topic_id, topic_name
            FROM topics
            WHERE chapter_id = %s
            """
            cursor.execute(query_topics, (chapter_id,))
            topics = cursor.fetchall()

            topic_data = [
                {
                    "topic_id": topic[0],
                    "topic_name": topic[1]
                }
                for topic in topics
            ]

            chapter_data.append({
                "chapter_id": chapter_id,
                "chapter_name": chapter_name,
                "topics": topic_data
            })

        return jsonify({
            "message": "Data fetched successfully",
            "data": chapter_data
        }), 200
    except Exception as e:
        return jsonify({"message": "Internal server error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
