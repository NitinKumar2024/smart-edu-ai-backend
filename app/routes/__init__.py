def init_routes(app):
    from app.routes.login import login_bp
    from app.routes.forgot_email import forgot_email_bp
    from app.routes.faculty_subject_assignments import faculty_bp
    from app.routes.notes_maker import notes_maker_bp
    from app.routes.question_paper_generator import faculty_question_paper_generator
    from app.routes.attendance.student_data import student_bp
    from app.routes.syllabus_extraction_logic import syllabus_extraction
    from app.routes.attendance.export_attendance_pdf import attendance_report

    app.register_blueprint(login_bp)
    app.register_blueprint(forgot_email_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(notes_maker_bp)
    app.register_blueprint(faculty_question_paper_generator)
    app.register_blueprint(student_bp)
    app.register_blueprint(syllabus_extraction)
    app.register_blueprint(attendance_report)
