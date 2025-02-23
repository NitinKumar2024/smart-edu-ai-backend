import markdown
import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound


class MarkdownConverter:
    def __init__(self):
        # Initialize markdown with extensions
        self.md = markdown.Markdown(extensions=[
            'fenced_code',  # For code blocks with ```
            'tables',  # For table support
            'nl2br',  # Convert newlines to <br>
            'sane_lists',  # Better list handling
            'pymdownx.superfences'  # Better fenced code blocks
        ])

        # Create HTML formatter for code highlighting
        self.formatter = HtmlFormatter(style='monokai', cssclass='highlight')

    def _process_code_blocks(self, html):
        """Process code blocks with syntax highlighting."""
        code_block_pattern = re.compile(
            r'<pre><code class="language-(\w+)">(.*?)</code></pre>',
            re.DOTALL
        )

        def replace_code_block(match):
            language, code = match.groups()
            try:
                lexer = get_lexer_by_name(language)
                highlighted = highlight(code, lexer, self.formatter)
                return highlighted
            except ClassNotFound:
                # If language isn't recognized, return as-is
                return f'<pre><code class="language-{language}">{code}</code></pre>'

        return code_block_pattern.sub(replace_code_block, html)

    def convert(self, markdown_text):
        """Convert markdown text to HTML with syntax highlighting."""
        # Convert markdown to HTML
        html = self.md.convert(markdown_text)

        # Process code blocks
        html = self._process_code_blocks(html)

        # Reset markdown instance
        self.md.reset()

        return html

    def get_css(self):
        """Get the CSS for code highlighting."""
        return self.formatter.get_style_defs('.highlight')


def main():
    # Example usage
    converter = MarkdownConverter()

    # Example markdown text
    markdown_text = """
# Hello World

This is a **bold** text and *italic* text.

Here's a Python code block:

```python
def hello_world():
    print("Hello, World!")
```

And here's a table:

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

1. First item
2. Second item
   - Nested item
   - Another nested item
"""

    # Convert to HTML
    html = converter.convert(markdown_text)

    # Get CSS for syntax highlighting
    css = converter.get_css()

    # Print the results
    print("=== CSS ===")
    print(css)
    print("\n=== HTML ===")
    print(html)


if __name__ == "__main__":
    main()