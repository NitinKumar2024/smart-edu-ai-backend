import json
import google.generativeai as genai
from flask import Blueprint
from flask import request, Response, stream_with_context, jsonify
from flask_cors import CORS

from app.models.api import api_key
from app.models.db import get_db_connection
from app.routes.faculty_subject_assignments import TokenValidator

notes_maker_bp = Blueprint('notes_maker', __name__)

CORS(notes_maker_bp)  # Enable CORS for all routes

genai.configure(api_key=api_key)
# Initialize model
model = genai.GenerativeModel('gemini-2.0-flash')

def check_existing_notes(topic_id):
    """
    Check if notes already exist for the given topic_id
    Returns the content and content_id if found, otherwise None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
        SELECT content_id, content 
        FROM topic_content 
        WHERE topic_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        cursor.execute(query, (topic_id,))
        result = cursor.fetchone()
        if result:
            return {"content_id": result[0], "content": result[1]}
        return None
    finally:
        cursor.close()
        conn.close()

def save_to_database(content, topic_id):
    """
    Save the generated content to the database
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO topic_content (content, topic_id)
        VALUES (%s, %s)
        """
        cursor.execute(query, (content, topic_id))
        content_id = cursor.lastrowid
        conn.commit()
        return content_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

@notes_maker_bp.route('/generate-notes', methods=['POST'])
def generate_notes():
    try:
        data = request.get_json()
        token = request.headers.get('Authorization')
        topic_id = data.get('topic_id')

        if not topic_id or not token:
            return jsonify({"error": "Missing topic_id or Authorization token"}), 400

        # Validate the token
        faculty_data, error = TokenValidator.validate_token(token)
        if error:
            return jsonify(error), 400 if "error" in error and error["error"] == "Invalid token" else 500

        # First, check if notes already exist
        existing_notes = check_existing_notes(topic_id)
        if existing_notes:
            # If notes exist, return them immediately
            return jsonify({
                "status": "exists",
                "content_id": existing_notes["content_id"],
                "content": existing_notes["content"]
            })

        # If no existing notes, fetch topic details for generation
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = """
            SELECT t.topic_name, c.chapter_name, s.Subject
            FROM topics t
            JOIN chapters c ON t.chapter_id = c.chapter_id
            JOIN allsubject s ON c.subject_id = s.subject_id
            WHERE t.topic_id = %s
            """
            cursor.execute(query, (topic_id,))
            result = cursor.fetchone()

            if not result:
                return jsonify({"error": "Invalid topic_id"}), 404

            topic_name, chapter_name, subject_name = result

        except Exception as e:
            return jsonify({"error": "Database error", "details": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

        # Prompt generation with easy explanations and enriched content
        message = f"""Generate clear, detailed, and focused notes on the topic '{topic_name}', which is part of the chapter '{chapter_name}' under the subject '{subject_name}'. 

        Requirements:
        1. Use simple, easy-to-understand language suitable for learners at any level. 
        2. Include relevant examples to illustrate key points clearly.
        3. Provide tables for comparisons, categorizations, or organized information where appropriate.
        4. If needed only, Add textual diagrams (such as step-by-step processes or hierarchical structures) to enhance understanding.
        5. Break down complex concepts into smaller, digestible parts with bullet points or numbered lists.
        6. Avoid phrases like "here is the explanation"; directly provide the notes.

        Your goal is to create engaging, learner-friendly notes that cover the topic comprehensively and efficiently. and do not write anything instead of notes"""

        def generate():
            try:
                response = model.generate_content(
                    message,
                    stream=True
                )

                # Initialize an empty string to collect all content
                full_content = ""

                for chunk in response:
                    if chunk.text:
                        full_content += chunk.text
                        # Yield the chunk for streaming
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"

                # After all content is generated, save to database
                try:
                    content_id = save_to_database(full_content, topic_id)
                    # Send a special message indicating successful storage
                    yield f"data: {json.dumps({'status': 'completed', 'content_id': content_id})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': f'Failed to save to database: {str(e)}'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500