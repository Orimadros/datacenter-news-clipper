import json
import os
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set PKG_CONFIG_PATH from .env before importing weasyprint
pkg_config_path = os.getenv('PKG_CONFIG_PATH')
if pkg_config_path:
    os.environ['PKG_CONFIG_PATH'] = pkg_config_path

from weasyprint import HTML

# ─────────────────────────────────────────────────────────────────────
# Paths (relative to services/ directory)
# ─────────────────────────────────────────────────────────────────────
SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SERVICES_DIR)
JSON_PATH = os.path.join(PROJECT_ROOT, "output", "clippings.json")
CONFIGS_DIR = os.path.join(PROJECT_ROOT, "configs")
OUTPUT_PDF = os.path.join(PROJECT_ROOT, "output", "clippings_output.pdf")  # Save PDF in output/

# ─────────────────────────────────────────────────────────────────────
# 1) Load the JSON clippings into Python and assign unique IDs
# ─────────────────────────────────────────────────────────────────────
def load_clippings(json_filepath):
    """
    Reads the JSON file containing a list of clipping dicts.
    Each dict must have: title, url, pubDate, source, summary.
    Adds a unique 'id' field to each clipping for in-page anchors.
    Returns a Python list of dicts.
    """
    with open(json_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Assign a unique anchor ID to each item (e.g. item-1, item-2, …)
    for idx, item in enumerate(data, start=1):
        item["id"] = f"item-{idx}"
    return data

# ─────────────────────────────────────────────────────────────────────
# 2) Initialize Jinja2 environment pointing to "configs/"
# ─────────────────────────────────────────────────────────────────────
def init_jinja2_environment(configs_dir):
    """
    Configures Jinja2 to load HTML templates from the configs directory.
    """
    env = Environment(
        loader=FileSystemLoader(configs_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env

# ─────────────────────────────────────────────────────────────────────
# 3) Render the HTML string using the Jinja2 template
# ─────────────────────────────────────────────────────────────────────
def render_html(env, template_name, items):
    """
    Given a Jinja2 Environment and template filename, render it with "items".
    Returns the complete HTML as a string.
    """
    template = env.get_template(template_name)
    html_content = template.render(
        items=items,
        today=datetime.now(),
        timedelta=timedelta
    )
    return html_content

# ─────────────────────────────────────────────────────────────────────
# 4) Convert the rendered HTML into a PDF via WeasyPrint
# ─────────────────────────────────────────────────────────────────────
def generate_pdf_from_html(html_string, output_path):
    """
    Uses WeasyPrint to write the given HTML string to a PDF file.
    We pass base_url=CONFIGS_DIR so that relative paths (e.g. your logo.png)
    resolve against configs/ where we'll place the image.
    """
    HTML(string=html_string, base_url=CONFIGS_DIR).write_pdf(output_path)

# ─────────────────────────────────────────────────────────────────────
# 5) Main orchestration
# ─────────────────────────────────────────────────────────────────────
def build_pdf():
    """
    Main function to generate PDF from clippings.json.
    """
    # Load data (with unique IDs for anchors)
    clippings = load_clippings(JSON_PATH)

    # Set up Jinja2
    env = init_jinja2_environment(CONFIGS_DIR)

    # Render HTML with our "clipping_template.html" template
    html_str = render_html(env, "clipping_template.html", clippings)

    # Convert to PDF (this will embed the header on every page)
    generate_pdf_from_html(html_str, OUTPUT_PDF)

    print(f"⚙️  PDF generated at: {OUTPUT_PDF}")
    return OUTPUT_PDF

if __name__ == "__main__":
    build_pdf()
