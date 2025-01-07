import json
import os
from datetime import datetime

import google.generativeai as genai
from flask import request, jsonify, make_response, Blueprint
from fpdf import FPDF

from app.models.api import api_key
from app.models.db import get_db_connection

faculty_question_paper_generator = Blueprint('faculty_question_paper_generator', __name__)

# Configure Gemini API
genai.configure(api_key=api_key)


class ExamPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Class Test', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'GOVERNMENT POLYTECHNIC BARH', 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')


def generate_questions(subject, topics, num_objective, num_short, num_long, difficulty_level):
    # Create a comma-separated string of topics
    topics_str = ", ".join([topic["name"] for chapter in topics for topic in chapter["topics"]])

    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    prompt = f"""
    Generate a set of {difficulty_level} difficulty level questions for an examination on the subject: {subject}.
    Cover the following topics: {topics_str}

    The exam should include:
    1. {num_objective} objective questions (multiple choice) with four options each
    2. {num_short} short answer questions
    3. {num_long} long answer questions

    Format the output as a JSON object with the following structure:
    {{
        "objective_questions": [
            {{
                "question": "Question text",
                "options": [
                    "A. Option A",
                    "B. Option B",
                    "C. Option C",
                    "D. Option D"
                ]
            }}
        ],
        "short_answer_questions": [
            {{
                "question": "Short answer question"
            }}
        ],
        "long_answer_questions": [
            {{
                "question": "Long answer question"
            }}
        ]
    }}

    Ensure the JSON is valid and properly formatted. Do not include any text before or after the JSON object.
    """

    response = model.generate_content(prompt)


    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        # Extract JSON from response if needed
        json_start = response.text.find('{')
        json_end = response.text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response.text[json_start:json_end]
            return json.loads(json_str)
        raise


def create_exam_pdf(subject, questions):
    pdf = ExamPDF(format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Exam Information
    pdf.set_font('Arial', 'B', 10)
    current_date = datetime.now().strftime("%Y-%m-%d")
    pdf.cell(95, 5, f'Subject: {subject}', 0, 0)
    pdf.cell(95, 5, f'Date: {current_date}', 0, 1, 'R')
    pdf.cell(95, 5, 'Time: 3 Hours', 0, 0)
    pdf.cell(95, 5, 'Total Marks: 100', 0, 1, 'R')
    pdf.ln(2)

    # Instructions
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'Instructions:', 0, 1)
    pdf.set_font('Arial', '', 9)
    instructions = [
        "1. Attempt all questions. Use blue or black ink only.",
        "2. Read each question carefully before answering.",
        "3. Write your answers clearly and concisely.",
        "4. For multiple-choice questions, circle the correct option."
    ]
    for instruction in instructions:
        pdf.cell(0, 4, instruction, 0, 1)
    pdf.ln(2)

    # Objective Questions
    if questions['objective_questions']:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'I. Objective Questions:', 0, 1)
        pdf.set_font('Arial', '', 10)
        for i, q in enumerate(questions['objective_questions'], 1):
            pdf.multi_cell(0, 5, f"{i}. {q['question']}")
            for option in q['options']:
                pdf.cell(0, 5, f"    {option}", 0, 1)
            pdf.ln(1)

    # Short Answer Questions
    if questions['short_answer_questions']:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'II. Short Answer Questions:', 0, 1)
        pdf.set_font('Arial', '', 10)
        for i, q in enumerate(questions['short_answer_questions'], 1):
            pdf.multi_cell(0, 5, f"{i}. {q['question']}")
            pdf.ln(3)

    # Long Answer Questions
    if questions['long_answer_questions']:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'III. Long Answer Questions:', 0, 1)
        pdf.set_font('Arial', '', 10)
        for i, q in enumerate(questions['long_answer_questions'], 1):
            pdf.multi_cell(0, 5, f"{i}. {q['question']}")
            pdf.ln(5)

    # Save PDF to a temporary file
    pdf_filename = f"exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename


def save_question_paper(conn, faculty_id, difficulty_level, questions_json):
    cursor = conn.cursor()
    try:
        # Insert into question_paper table
        insert_query = """
        INSERT INTO question_paper (faculty_id, difficulty_level, questions)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (faculty_id, difficulty_level, json.dumps(questions_json)))

        # Get the generated question_paper_id
        question_paper_id = cursor.lastrowid
        conn.commit()
        return question_paper_id

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


def save_question_paper_topics(conn, question_paper_id, topics):
    cursor = conn.cursor()
    try:
        # Insert topic mappings
        insert_query = """
        INSERT INTO question_paper_topic (question_paper_id, topic_id)
        VALUES (%s, %s)
        """
        topic_values = [(question_paper_id, topic["topic_id"])
                        for chapter in topics
                        for topic in chapter["topics"]]

        cursor.executemany(insert_query, topic_values)
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


@faculty_question_paper_generator.route('/generate-exam', methods=['POST'])
def generate_exam():
    conn = None
    try:
        data = request.get_json()

        # Extract data from request
        subject = data['subject']
        faculty_id = data['faculty_id']
        difficulty_level = data['difficulty_level']
        num_objective = data['num_objective']
        num_short = data['num_short']
        num_long = data['num_long']
        chapters = data['chapters']

        # Generate questions
        questions = generate_questions(
            subject,
            chapters,
            num_objective,
            num_short,
            num_long,
            difficulty_level
        )

        # Get database connection
        conn = get_db_connection()

        # Save to database
        question_paper_id = save_question_paper(conn, faculty_id, difficulty_level, questions)
        save_question_paper_topics(conn, question_paper_id, chapters)

        # Generate PDF
        pdf_filename = create_exam_pdf(subject, questions)

        # Read the PDF file
        with open(pdf_filename, 'rb') as pdf_file:
            pdf_data = pdf_file.read()

        # Clean up the temporary file
        os.remove(pdf_filename)

        # Create response with file data and headers
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=exam_{question_paper_id}.pdf'
        response.headers['Question-Paper-ID'] = str(question_paper_id)
        response.headers['Message'] = 'Exam generated successfully'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Close database connection
        if conn:
            conn.close()
