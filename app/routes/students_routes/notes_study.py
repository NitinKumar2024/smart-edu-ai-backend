import markdown
from flask import Blueprint, jsonify

from app.models.db import get_db_connection

notes_bp = Blueprint('notes', __name__)


def enhance_ascii_art(content):
    """Preserve ASCII art diagrams by wrapping them in pre tags"""
    lines = content.split('\n')
    in_ascii_art = False
    enhanced_lines = []

    for line in lines:
        # Detect ASCII art based on common characters
        if any(char in line for char in '+-|┌┐└┘─│╔╗╚╝═║'):
            if not in_ascii_art:
                enhanced_lines.append('<pre class="ascii-art">')
                in_ascii_art = True
        elif in_ascii_art:
            enhanced_lines.append('</pre>')
            in_ascii_art = False

        enhanced_lines.append(line)

    if in_ascii_art:
        enhanced_lines.append('</pre>')

    return '\n'.join(enhanced_lines)


def process_markdown(content):
    """Process markdown with enhanced formatting"""
    # First enhance ASCII art
    content = enhance_ascii_art(content)

    # Configure markdown extensions
    md = markdown.Markdown(extensions=[
        'extra',  # Includes tables, footnotes, and more
        'codehilite',  # Syntax highlighting for code blocks
        'fenced_code',  # Fenced code blocks
        'tables',  # Enhanced table support
        'attr_list',  # Attribute lists
        'def_list',  # Definition lists
        'nl2br',  # New line to break conversion
    ])

    # Convert to HTML
    html_content = md.convert(content)

    # Add custom CSS classes
    html_content = html_content.replace('<table>', '<table class="md-table">')
    html_content = html_content.replace('<code>', '<code class="md-code">')

    return html_content


@notes_bp.route('/api/notes/content/<int:topic_id>', methods=['GET'])
def get_notes_content(topic_id):
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute query to fetch content
        query = """
            SELECT content_id, content 
            FROM topic_content 
            WHERE topic_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        cursor.execute(query, (topic_id,))
        result = cursor.fetchone()

        # Close database connection
        cursor.close()
        conn.close()

        if result is None:
            return jsonify({
                'status': 'error',
                'message': 'No content found for this topic'
            }), 404

        # Parse markdown content with enhanced formatting
        content_id, md_content = result
        html_content = process_markdown(md_content)

        # Add recommended CSS styles
        css_styles = """
        .md-table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        .md-table th, .md-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .md-table th {
            background-color: #f5f5f5;
        }
        .ascii-art {
            font-family: monospace;
            white-space: pre;
            background-color: #f5f5f5;
            padding: 1em;
            border-radius: 4px;
            overflow-x: auto;
        }
        .md-code {
            background-color: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: monospace;
        }
        """

        return jsonify({
            'status': 'success',
            'data': {
                'content_id': content_id,
                'content': md_content

            }
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500