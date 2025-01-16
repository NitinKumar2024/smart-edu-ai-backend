import io
from collections import defaultdict

from flask import Blueprint, request, jsonify, send_file
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

from app.models.db import get_db_connection

attendance_report = Blueprint('attendance_report', __name__)


@attendance_report.route('/attendance-report', methods=['GET'])
def generate_attendance_report():
    try:
        # Get parameters from request
        subject_id = request.args.get('subject_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([subject_id, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get subject details
        subject_query = """
            SELECT Subject, Subject_Code, Branch_Code, semester, college_code 
            FROM allsubject 
            WHERE subject_id = %s
        """
        cursor.execute(subject_query, (subject_id,))
        subject_info = cursor.fetchone()

        if not subject_info:
            return jsonify({'error': 'Subject not found'}), 404

        # Convert tuple to dictionary
        subject_info = {
            'Subject': subject_info[0],
            'Subject_Code': subject_info[1],
            'Branch_Code': subject_info[2],
            'semester': subject_info[3],
            'college_code': subject_info[4]
        }

        # Get attendance data
        attendance_query = """
            SELECT 
                a.date,
                s.username,
                s.Reg,
                a.status,
                GROUP_CONCAT(t.topic_name) as topics
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            LEFT JOIN attendance_topics at ON a.attendance_id = at.attendance_id
            LEFT JOIN topics t ON at.topic_id = t.topic_id
            WHERE a.subject_id = %s
            AND a.date BETWEEN %s AND %s
            GROUP BY a.date, a.student_id
            ORDER BY a.date, s.username
        """
        cursor.execute(attendance_query, (subject_id, start_date, end_date))
        attendance_records = cursor.fetchall()

        # Organize data by date
        attendance_by_date = defaultdict(list)
        topics_by_date = {}
        for record in attendance_records:
            date = record[0]
            attendance_by_date[date].append({
                'username': record[1],
                'Reg': record[2],
                'status': record[3]
            })
            if date not in topics_by_date:
                topics_by_date[date] = record[4]

        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=HexColor('#1a237e')  # Dark blue color
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#283593'),
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        elements = []

        # Add title
        elements.append(Paragraph(f"Attendance Report", title_style))

        # Add subject information in a table
        info_data = [
            ['Subject', subject_info['Subject']],
            ['Subject Code', subject_info['Subject_Code']],
            ['Branch', subject_info['Branch_Code']],
            ['Semester', str(subject_info['semester'])],
            ['College Code', subject_info['college_code']],
            ['Period', f"{start_date} to {end_date}"]
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#e3f2fd')),  # Light blue
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#1a237e')),  # Dark blue
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
            ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2'))
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # Add attendance data for each date
        for date, students in attendance_by_date.items():
            # Date header
            date_str = date.strftime('%B %d, %Y')
            elements.append(Paragraph(f"Date: {date_str}", heading_style))

            # Topics covered
            topics = topics_by_date[date] or 'No topics recorded'
            elements.append(Paragraph(f"Topics Covered: {topics}", normal_style))
            elements.append(Spacer(1, 10))

            # Attendance table
            attendance_data = [['Student Name', 'Registration', 'Status']]
            for student in students:
                attendance_data.append([
                    student['username'],
                    student['Reg'],
                    student['status']
                ])

            attendance_table = Table(attendance_data, colWidths=[3 * inch, 2 * inch, 1.5 * inch])
            attendance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1976d2')),  # Header blue
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
                ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f5f5f5'), colors.white]),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(attendance_table)
            elements.append(Spacer(1, 20))

            # Add summary for this date
            present_count = sum(1 for s in students if s['status'] == "present")
            total_students = len(students)
            attendance_rate = (present_count / total_students) * 100 if total_students > 0 else 0

            summary_data = [
                ['Total Students', 'Present', 'Absent', 'Attendance Rate'],
                [
                    str(total_students),
                    str(present_count),
                    str(total_students - present_count),
                    f"{attendance_rate:.1f}%"
                ]
            ]

            summary_table = Table(summary_data, colWidths=[2 * inch] * 4)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e3f2fd')),
                ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#1a237e')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
                ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2'))
            ]))
            elements.append(summary_table)
            elements.append(PageBreak())

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        cursor.close()
        conn.close()

        # Return PDF file
        return send_file(
            buffer,
            download_name=f'attendance_report_{subject_id}_{start_date}_{end_date}.pdf',
            mimetype='application/pdf',
            as_attachment=True
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_report.route('/attendance-summary', methods=['GET'])
def generate_attendance_summary():
    try:
        # Get parameters from request
        subject_id = request.args.get('subject_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([subject_id, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get subject details
        subject_query = """
            SELECT Subject, Subject_Code, Branch_Code, semester, college_code 
            FROM allsubject 
            WHERE subject_id = %s
        """
        cursor.execute(subject_query, (subject_id,))
        subject_info = cursor.fetchone()

        if not subject_info:
            return jsonify({'error': 'Subject not found'}), 404

        # Convert tuple to dictionary
        subject_info = {
            'Subject': subject_info[0],
            'Subject_Code': subject_info[1],
            'Branch_Code': subject_info[2],
            'semester': subject_info[3],
            'college_code': subject_info[4]
        }

        # Get attendance summary data
        summary_query = """
            SELECT 
                s.username,
                s.Reg,
                COUNT(a.attendance_id) as total_classes,
                SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                ROUND((SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.attendance_id)), 2) as attendance_percentage
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id
            WHERE a.subject_id = %s 
            AND a.date BETWEEN %s AND %s
            GROUP BY s.student_id, s.username, s.Reg
            ORDER BY s.username
        """
        cursor.execute(summary_query, (subject_id, start_date, end_date))
        summary_records = cursor.fetchall()

        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,
            textColor=HexColor('#1a237e')
        )

        elements = []

        # Add title
        elements.append(Paragraph("Attendance Summary Report", title_style))

        # Add subject information
        info_data = [
            ['Subject', subject_info['Subject']],
            ['Subject Code', subject_info['Subject_Code']],
            ['Branch', subject_info['Branch_Code']],
            ['Semester', str(subject_info['semester'])],
            ['College Code', subject_info['college_code']],
            ['Period', f"{start_date} to {end_date}"]
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#1a237e')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
            ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2'))
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 30))

        # Create summary table
        table_headers = ['Student Name', 'Registration', 'Total Classes', 'Present', 'Absent', 'Attendance %']
        table_data = [table_headers]

        for record in summary_records:
            table_data.append([
                record[0],  # username
                record[1],  # reg
                str(record[2]),  # total_classes
                str(record[3]),  # present_count
                str(record[4]),  # absent_count
                f"{record[5]}%"  # attendance_percentage
            ])

        # Add overall statistics
        if summary_records:
            total_students = len(summary_records)
            avg_attendance = sum(record[5] for record in summary_records) / total_students
            students_above_75 = sum(1 for record in summary_records if record[5] >= 75)

            stats_data = [
                ['Total Students', 'Average Attendance', 'Students ≥75% Attendance'],
                [
                    str(total_students),
                    f"{avg_attendance:.2f}%",
                    f"{students_above_75} ({(students_above_75 / total_students) * 100:.1f}%)"
                ]
            ]

            stats_table = Table(stats_data, colWidths=[2.5 * inch] * 3)
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e3f2fd')),
                ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#1a237e')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
                ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2'))
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 20))

        # Style the main summary table
        summary_table = Table(table_data, colWidths=[2.5 * inch, 1.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#bbdefb')),
            ('BOX', (0, 0), (-1, -1), 2, HexColor('#1976d2')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f5f5f5'), colors.white]),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        cursor.close()
        conn.close()

        # Return PDF file
        return send_file(
            buffer,
            download_name=f'attendance_summary_{subject_id}_{start_date}_{end_date}.pdf',
            mimetype='application/pdf',
            as_attachment=True
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
