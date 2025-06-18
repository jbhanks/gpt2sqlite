import sys
import sqlite3
import sqlite3
from jinja2 import Template
from pathlib import Path
import re
import html as htmllib  # avoid name conflict
from itertools import cycle

# Nice pastel colors
COLOR_PALETTE = [
    "#e0f7fa",  # cyan
    "#f1f8e9",  # light green
    "#fce4ec",  # pink
    "#fff3e0",  # orange
    "#ede7f6",  # lavender
    "#e8f5e9",  # pale green
    "#f3e5f5",  # light purple
    "#e1f5fe",  # light blue
    "#f9fbe7",  # lime
    "#efebe9",  # stone
]

model_slug_colors = {}


dbpath = sys.argv[1]
outpath = sys.argv[2]

# Output folder
output_dir = Path(outpath)
output_dir.mkdir(exist_ok=True)


# -- Configuration --
DB_PATH = sys.argv[1]
OUTPUT_DIR = Path(sys.argv[2])

# -- Ensure output directory exists --
OUTPUT_DIR.mkdir(exist_ok=True)

# -- Code block converter --
def convert_code_blocks(text):
    if text is None:
        return None

    # Convert triple backticks to <pre><code>
    def repl_block(match):
        code = htmllib.escape(match.group(1))
        return f"<pre><code>{code}</code></pre>"

    text = re.sub(r"```(.*?)```", repl_block, text, flags=re.DOTALL)

    # Convert inline backticks to <code>
    def repl_inline(match):
        code = htmllib.escape(match.group(1))
        return f"<code>{code}</code>"

    text = re.sub(r"`([^`\n]+?)`", repl_inline, text)

    return text

# -- HTML template --
html_template = Template("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>
    body { font-family: sans-serif; line-height: 1.6; }
    .meta { font-size: 0.9em; color: gray; margin-top: 0.25em; }
    hr { margin: 2em 0; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  {% for block in content_blocks %}
    <div style="background-color: {{ block.bgcolor }}; padding: 1em; border-radius: 8px; margin-bottom: 2em;">
      <p>{{ block.content | safe }}</p>
      <sub>{{ block.create_time }} · {{ block.model_slug }}</sub>
    </div>
    <hr>
  {% endfor %}
</body>
</html>
""")

# -- Database connection --
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# -- Get table names --
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row["name"] for row in cursor.fetchall()]

model_slugs = set()

for table in tables:
    try:
        cursor.execute(f"SELECT DISTINCT model_slug FROM {table}")
        model_slugs.update(row["model_slug"] for row in cursor.fetchall() if row["model_slug"] is not None)
    except sqlite3.OperationalError:
        continue

# Assign each model_slug a color from the palette
color_cycle = cycle(COLOR_PALETTE)
for slug in sorted(model_slugs):  # deterministic
    model_slug_colors[slug] = next(color_cycle)

# -- Process each table --
for table in tables:
  try:
    cursor.execute(f"SELECT content, create_time, model_slug FROM {table}")
    rows = cursor.fetchall()
    content_blocks = []
    for row in rows:
        content = convert_code_blocks(row["content"])
        if content is None:
            continue
        color = model_slug_colors.get(row["model_slug"], "#ffffff")
        content_blocks.append({
            "content": content,
            "create_time": row["create_time"],
            "model_slug": row["model_slug"],
            "bgcolor": color
        })
    rendered_html = html_template.render(
        title=re.sub('_', ' ', re.sub('chat_[0-9]+_(.*)_?$', r'\1', table).capitalize()),
        content_blocks=content_blocks
    )

    output_path = OUTPUT_DIR / f"{table}.html"
    output_path.write_text(rendered_html, encoding="utf-8")
  except sqlite3.OperationalError:
    continue
print(f"✅ Exported {len(tables)} HTML files to {OUTPUT_DIR.resolve()}")
