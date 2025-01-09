from flask import Blueprint, request, jsonify
from app.models.db import get_db_connection
from app.routes.faculty_subject_assignments import TokenValidator


# Create a Blueprint
student_bp = Blueprint('student_data', __name__)

# Define the route to fetch student data
@student_bp.route('/student-data', methods=['GET'])
def get_students():
    # Get parameters from the request
    semester = request.args.get('semester')
    branch = request.args.get('branch')
    college_code = request.args.get('college_code')

    # Validate required parameters
    if not all([semester, branch, college_code]):
        return jsonify({"error": "Missing required parameters."}), 400

    try:
        # Get database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Define the query to fetch data from the students table
        query = """
        SELECT username, Reg, email, student_id, number
        FROM students
        WHERE semester = %s AND branch = %s AND college_code = %s
        """

        # Execute the query with the provided parameters
        cursor.execute(query, (semester, branch, college_code))
        students = cursor.fetchall()

        # Map the data into a list of dictionaries
        student_list = [
            {
                "username": row[0],
                "Reg": row[1],
                "email": row[2],
                "student_id": row[3],
                "number": row[4]
            } for row in students
        ]

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Return the JSON response
        return jsonify({
            "message": "successful",
            "data": {
                "all_students": student_list
            }
        }), 200


    except Exception as e:
        # Handle any exceptions and return an error response
        return jsonify({"error": str(e)}), 500


@student_bp.route('/add_bulk_attendance', methods=['POST'])
def add_bulk_attendance():
    try:
        # Parse JSON data from the request
        data = request.get_json()
        student_attendance = data.get('student_attendance')  # List of attendance records

        # Validate input data
        if not student_attendance or not isinstance(student_attendance, list):
            return jsonify({'error': 'Invalid input data, expected a list of student attendance records'}), 400

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Process each student's attendance record
        for record in student_attendance:
            student_id = record.get('student_id')
            subject_id = record.get('subject_id')
            status = record.get('status', 'absent')  # Default to 'absent'
            topic_ids = record.get('topic_ids')  # List of topic IDs

            # Validate individual record
            if not student_id or not subject_id or not topic_ids or not isinstance(topic_ids, list):
                return jsonify({'error': f'Invalid record for student_id: {student_id}'}), 400

            # Insert attendance record
            cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, date, status)
                VALUES (%s, %s, CURDATE(), %s)
            """, (student_id, subject_id, status))

            # Get the inserted attendance_id
            attendance_id = cursor.lastrowid

            # Insert records into the attendance_topics table
            for topic_id in topic_ids:
                cursor.execute("""
                    INSERT INTO attendance_topics (attendance_id, topic_id)
                    VALUES (%s, %s)
                """, (attendance_id, topic_id))

        # Commit the transaction
        conn.commit()

        return jsonify({'message': 'Bulk attendance added successfully'}), 201

    except Exception as e:
        # Rollback in case of any error
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        # Close the database connection
        if conn:
            cursor.close()
            conn.close()