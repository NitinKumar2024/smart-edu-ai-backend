from flask import Blueprint, request, jsonify

from app.models.db import get_db_connection

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/attendance_details', methods=['GET'])
def get_attendance_details():
    try:
        # Get parameters from request
        subject_id = request.args.get('subject_id')
        student_id = request.args.get('student_id')

        if not subject_id or not student_id:
            return jsonify({
                'error': 'Both subject_id and student_id are required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get attendance records with topics
        cursor.execute("""
            SELECT 
                a.attendance_id,
                a.date,
                a.status,
                c.chapter_name,
                t.topic_name
            FROM attendance a
            LEFT JOIN attendance_topics at ON a.attendance_id = at.attendance_id
            LEFT JOIN topics t ON at.topic_id = t.topic_id
            LEFT JOIN chapters c ON t.chapter_id = c.chapter_id
            WHERE a.subject_id = %s AND a.student_id = %s
            ORDER BY a.date DESC
        """, (subject_id, student_id))

        attendance_records = cursor.fetchall()

        # Calculate attendance statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_classes,
                SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as classes_attended
            FROM attendance
            WHERE subject_id = %s AND student_id = %s
        """, (subject_id, student_id))

        attendance_stats = cursor.fetchone()

        # Process the results
        attendance_details = []
        for record in attendance_records:
            attendance_details.append({
                'attendance_id': record[0],
                'date': record[1].strftime('%Y-%m-%d'),
                'status': record[2],
                'chapter': record[3],
                'topic': record[4]
            })

        # Calculate attendance percentage
        total_classes = attendance_stats[0]
        classes_attended = attendance_stats[1]
        attendance_percentage = (classes_attended / total_classes * 100) if total_classes > 0 else 0

        response = {

            'attendance_statistics': {
                'total_classes': total_classes,
                'classes_attended': classes_attended,
                'attendance_percentage': round(attendance_percentage, 2)
            },
            'attendance_records': attendance_details
        }

        cursor.close()
        conn.close()

        return jsonify({
            'message': 'success',
            'data': response
        })

    except Exception as e:
        return jsonify({
            'error': 'An error occurred while fetching attendance details',
            'message': str(e)
        }), 500