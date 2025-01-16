
import json
import os
import time

import google.generativeai as genai
from flask import request, jsonify, Blueprint
from flask_cors import CORS
from werkzeug.utils import secure_filename

from app.models.api import api_key
from app.models.db import get_db_connection

syllabus_extraction = Blueprint('syllabus_extraction', __name__)


CORS(syllabus_extraction, resources={
    r"/api/*": {
        "origins": [
            "https://turbocampuspro.com",
            "https://smarteduai.turbocampuspro.com"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_gemini_response(response_text):
    """Clean the Gemini response text to get valid JSON"""
    response_text = response_text.replace('```json', '').replace('```', '')
    try:
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1:
            json_str = response_text[start:end + 1]
            return json.loads(json_str)
    except Exception as e:
        print(f"Error cleaning response: {str(e)}")
        return None


def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    return file


def wait_for_files_active(files):
    """Waits for the given files to be active."""
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")


def extract_syllabus(pdf_path, known_subjects):
    """Extract syllabus data using Gemini"""
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    files = [upload_to_gemini(pdf_path, mime_type="application/pdf")]
    wait_for_files_active(files)

    prompt = f"""
    Extract information from this syllabus PDF into a structured JSON format.
    Do not include any markdown formatting or code block markers in your response.
    Return only the raw JSON data.

    Use these known subject codes and names for reference:
    {known_subjects}

    Return the data in this exact structure:
    {{
        "subjects": [
            {{
                "subject_code": "string",
                "subject_name": "string (must match known subjects)",
                "chapters": [
                    {{
                        "unit_number": "number",
                        "chapter_name": "string",
                        "topics": []
                    }}
                ]
            }}
        ]
    }}
    
    Important points to extract:
 
1. Match subjects with the provided known_subjects list
2. Each unit/chapter starts with "Unit-" or "Unit" followed by number
3. Extract ALL topics under each unit
4. Capture complete topic hierarchies

Please provide ONLY the JSON output, no additional text.
also remember topic is not too long it is logical
    """

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": ["You are a syllabus extractor tool. Return only raw JSON data."] + [files[0]]
            }
        ]
    )

    response = chat_session.send_message(prompt)
    print(response.text)
    return clean_gemini_response(response.text)


def save_to_database(data, branch_code, semester, college_code):
    """Save the extracted and edited syllabus to database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for subject in data['subjects']:
                # Insert subject
                sql = """
                    INSERT INTO allsubject (Subject_Code, Subject, Branch_Code, semester, college_code) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    subject['subject_code'],
                    subject['subject_name'],
                    branch_code,
                    semester,
                    college_code
                ))
                subject_id = cursor.lastrowid

                # Insert chapters and topics
                for chapter in subject['chapters']:
                    sql = """
                        INSERT INTO chapters (chapter_name, subject_id) 
                        VALUES (%s, %s)
                    """
                    cursor.execute(sql, (chapter['chapter_name'], subject_id))
                    chapter_id = cursor.lastrowid

                    for topic in chapter['topics']:
                        sql = """
                            INSERT INTO topics (topic_name, chapter_id) 
                            VALUES (%s, %s)
                        """
                        cursor.execute(sql, (topic, chapter_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Database error: {str(e)}")
        return False
    finally:
        conn.close()


@syllabus_extraction.route('/api/extract-syllabus', methods=['POST'])
def extract_syllabus_endpoint():
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Get other parameters
        branch_code = request.form.get('branch_code')
        semester = request.form.get('semester')
        college_code = request.form.get('college_code')
        known_subjects = request.form.get('known_subjects')

        if not all([branch_code, semester, college_code, known_subjects]):
            return jsonify({'error': 'Missing required parameters'}), 400

        try:
            known_subjects = json.loads(known_subjects)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid known_subjects format'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join("uploads", filename)
            file.save(filepath)

            # Extract syllabus data
            try:
                syllabus_data = extract_syllabus(filepath, known_subjects)
                if syllabus_data:
                    return jsonify({
                        'status': 'success',
                        'data': syllabus_data
                    })
                else:
                    return jsonify({'error': 'Failed to extract syllabus data'}), 500
            finally:
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            return jsonify({'error': 'Invalid file type'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@syllabus_extraction.route('/api/save-syllabus', methods=['POST'])
def save_syllabus_endpoint():
    try:
        data = request.json

        # Validate required fields
        required_fields = ['syllabus_data', 'branch_code', 'semester', 'college_code']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Save to database
        success = save_to_database(
            data['syllabus_data'],
            data['branch_code'],
            data['semester'],
            data['college_code']
        )

        if success:
            return jsonify({'status': 'success', 'message': 'Syllabus saved successfully'})
        else:
            return jsonify({'error': 'Failed to save syllabus'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


