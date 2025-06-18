import sqlite3
from jinja2 import Template
from pathlib import Path
import re
import sys

dbpath = sys.argv[1]
outpath = sys.argv[2]

# Connect to your SQLite database
conn = sqlite3.connect(dbpath)
conn.row_factory = sqlite3.Row  # Access columns by name
cursor = conn.cursor()

# Output folder
output_dir = Path(outpath)
output_dir.mkdir(exist_ok=True)

# Template for each HTML document
html_template = Template("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>
    body { font-family: sans-serif; line-height: 1.6; }
    .meta { font-size: 0.9em; color: gray; margin-top: 0.25em; }
    .role { font-size: 1.1em; color: black; margin-top: 0.25em; }
    hr { margin: 2em 0; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  {% for block in content_blocks %}
    <p><b>{{ block.role }}:</b></p>
    <p>{{ block.content }}</p>
    <div class="meta">{{ block.create_time }} · {{ block.model_slug }}</div>
    <hr>
  {% endfor %}
</body>
</html>
""")

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row["name"] for row in cursor.fetchall()]

for table in tables:
  try:
    cursor.execute(f"SELECT content, role, create_time, model_slug FROM {table}")
    rows = cursor.fetchall()

    html = html_template.render(
        title=re.sub('_', ' ', re.sub('chat_[0-9]+_(.*)_', r'\1', table).capitalize()),
        content_blocks=[
            {
                "content": row["content"],
                "role": row["role"],
                "create_time": row["create_time"],
                "model_slug": row["model_slug"]
            }
            for row in rows
        ]
    )

    (output_dir / f"{table}.html").write_text(html, encoding="utf-8")
  except sqlite3.OperationalError:
    continue

print(f"✅ HTML files saved to {output_dir.resolve()}")
