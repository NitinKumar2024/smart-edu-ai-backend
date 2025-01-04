def init_routes(app):
    from app.routes.login import login_bp
    from app.routes.forgot_email import forgot_email_bp
    from app.routes.faculty_subject_assignments import faculty_bp

    app.register_blueprint(login_bp)
    app.register_blueprint(forgot_email_bp)
    app.register_blueprint(faculty_bp)
