"""Runeform POC 3 — web server with structured intake form and diagnostic results."""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from runeform.brand import export_zip, import_zip, load_brand, save_brand
from runeform.models import BrandKit, EventData
from runeform.pipeline import generate, OUTPUT_DIR

app = FastAPI(title="Runeform POC 3")

OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

UPLOADS_DIR = Path("uploads")

# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------

BASE_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f8f4ee;
    color: #333;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60px 20px;
  }
  h1 { font-size: 2rem; margin-bottom: 4px; letter-spacing: -0.02em; }
  .subtitle { color: #888; margin-bottom: 8px; font-size: 0.95rem; }
  .badge {
    display: inline-block;
    background: #e8e4de;
    color: #666;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 32px;
    letter-spacing: 0.03em;
  }
  .card-box {
    background: white;
    border-radius: 12px;
    padding: 32px;
    max-width: 520px;
    width: 100%;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 20px;
  }
  label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; }
  .hint { color: #999; font-size: 0.8rem; margin-bottom: 8px; }
  input[type="text"], input[type="color"], textarea {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 0.95rem;
    font-family: inherit;
    margin-bottom: 20px;
  }
  textarea { resize: vertical; min-height: 80px; }
  input:focus, textarea:focus { outline: none; border-color: #666; }
  .row { display: flex; gap: 16px; }
  .row > div { flex: 1; }
  input[type="file"] { margin-bottom: 20px; font-size: 0.9rem; }
  button, .btn {
    display: inline-block;
    padding: 12px 20px;
    background: #333;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
    text-decoration: none;
    text-align: center;
  }
  button:hover, .btn:hover { background: #555; }
  .btn-full { width: 100%; display: block; }
  .btn-outline {
    background: white;
    color: #333;
    border: 2px solid #ddd;
  }
  .btn-outline:hover { background: #f8f4ee; border-color: #bbb; }
  nav {
    display: flex;
    gap: 16px;
    margin-bottom: 32px;
  }
  nav a {
    color: #888;
    text-decoration: none;
    font-size: 0.85rem;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
  }
  nav a:hover { color: #333; }
  nav a.active { color: #333; border-bottom-color: #333; }
  .brand-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #e8f5e9;
    color: #2e7d32;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 20px;
  }
  .brand-status.none {
    background: #fff3e0;
    color: #e65100;
  }
  .color-inputs { display: flex; gap: 10px; margin-bottom: 20px; }
  .color-inputs input[type="color"] {
    width: 50px; height: 40px; padding: 2px;
    border: 2px solid #ddd; border-radius: 8px; cursor: pointer;
    margin-bottom: 0;
  }
  .color-inputs .color-slot { text-align: center; }
  .color-inputs .color-label { font-size: 0.7rem; color: #999; }
"""


def _nav_html(active: str) -> str:
    def cls(name: str) -> str:
        return ' class="active"' if name == active else ""
    return f"""
    <nav>
      <a href="/"{cls("generate")}>Generate</a>
      <a href="/brand"{cls("brand")}>Brand Kit</a>
    </nav>"""


def _brand_status_html() -> str:
    loaded = load_brand()
    if loaded:
        brand, _ = loaded
        return f'<span class="brand-status">{brand.name}</span>'
    return '<span class="brand-status none">No brand configured</span>'


# ---------------------------------------------------------------------------
# Generate page
# ---------------------------------------------------------------------------

def _generate_form_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Runeform POC 3</title>
<style>{BASE_CSS}</style>
</head>
<body>
  <h1>Runeform</h1>
  <p class="subtitle">Describe your event. Get ready-to-post graphics.</p>
  <span class="badge">POC 3 — Z3 Typography + Data Shape Analysis</span>
  {_nav_html("generate")}
  {_brand_status_html()}
  <form class="card-box" method="POST" action="/generate" enctype="multipart/form-data">
    <label for="title">Event Title *</label>
    <input type="text" id="title" name="title" required placeholder="Morning Flow Yoga">

    <div class="row">
      <div>
        <label for="date">Date</label>
        <input type="text" id="date" name="date" placeholder="Sunday March 15">
      </div>
      <div>
        <label for="time">Time</label>
        <input type="text" id="time" name="time" placeholder="9:00 AM">
      </div>
    </div>

    <label for="location">Location</label>
    <input type="text" id="location" name="location" placeholder="Serenity Woods Outdoor Studio">

    <label for="description">Description</label>
    <textarea id="description" name="description" placeholder="Beginner-friendly, mats provided, all levels welcome"></textarea>

    <label for="image">Image (optional)</label>
    <p class="hint">Upload a hero photo, or leave empty for mock photos</p>
    <input type="file" id="image" name="image" accept="image/*">

    <button type="submit" class="btn-full">Generate Graphics</button>
  </form>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Brand Kit page
# ---------------------------------------------------------------------------

def _brand_form_html(brand: BrandKit | None = None, logo_path: Path | None = None, message: str = "") -> str:
    name_val = brand.name if brand else ""
    addr_val = brand.address if brand else ""
    desc_val = brand.description if brand else ""
    c1 = brand.colors[0] if brand and len(brand.colors) > 0 else "#333333"
    c2 = brand.colors[1] if brand and len(brand.colors) > 1 else "#888888"
    c3 = brand.colors[2] if brand and len(brand.colors) > 2 else "#f8f4ee"

    logo_html = ""
    if logo_path and logo_path.exists():
        logo_html = f"""
        <div style="margin-bottom:16px;">
          <p class="hint">Current logo:</p>
          <img src="/brand-logo" style="max-height:80px; border-radius:8px; border:1px solid #ddd;">
        </div>"""

    msg_html = ""
    if message:
        msg_html = f'<div style="background:#e8f5e9;color:#2e7d32;padding:10px 14px;border-radius:8px;margin-bottom:20px;font-size:0.9rem;">{message}</div>'

    export_html = ""
    if brand:
        export_html = '<a href="/brand/export" class="btn btn-outline btn-full" style="margin-top:12px;">Download Brand Kit (.zip)</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Runeform — Brand Kit</title>
<style>{BASE_CSS}</style>
</head>
<body>
  <h1>Runeform</h1>
  <p class="subtitle">Configure your brand identity.</p>
  <span class="badge">Brand Kit</span>
  {_nav_html("brand")}
  {msg_html}

  <form class="card-box" method="POST" action="/brand" enctype="multipart/form-data">
    <label for="brand_name">Brand Name *</label>
    <input type="text" id="brand_name" name="brand_name" required placeholder="Sequoia Fabrica" value="{name_val}">

    <label for="address">Address</label>
    <input type="text" id="address" name="address" placeholder="123 Main St, Portland, OR" value="{addr_val}">

    <label>Brand Colors</label>
    <p class="hint">Primary, secondary, and accent colors</p>
    <div class="color-inputs">
      <div class="color-slot">
        <input type="color" name="color1" value="{c1}">
        <div class="color-label">Primary</div>
      </div>
      <div class="color-slot">
        <input type="color" name="color2" value="{c2}">
        <div class="color-label">Secondary</div>
      </div>
      <div class="color-slot">
        <input type="color" name="color3" value="{c3}">
        <div class="color-label">Accent</div>
      </div>
    </div>

    <label for="brand_description">Brand Description</label>
    <p class="hint">Describe your brand's vibe — influences aesthetic choices</p>
    <textarea id="brand_description" name="brand_description" placeholder="A community makerspace focused on woodworking, electronics, and art. Warm, approachable, hands-on.">{desc_val}</textarea>

    <label for="logo">Logo</label>
    <p class="hint">Upload your brand logo (PNG or SVG recommended)</p>
    {logo_html}
    <input type="file" id="logo" name="logo" accept="image/*">

    <button type="submit" class="btn-full">Save Brand Kit</button>
    {export_html}
  </form>

  <div class="card-box">
    <label>Import Brand Kit</label>
    <p class="hint">Upload a previously exported .zip brand kit</p>
    <form method="POST" action="/brand/import" enctype="multipart/form-data">
      <input type="file" name="brand_zip" accept=".zip" required>
      <button type="submit" class="btn-full btn-outline">Import from Zip</button>
    </form>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------

def _results_html(result) -> str:
    ds = result.data_shape

    diag = f"""
    <div class="diag">
      <h3>Pipeline Diagnostics</h3>
      <div class="diag-grid">
        <div class="diag-card">
          <span class="diag-label">Content Type</span>
          <span class="diag-value">{ds.content_type.value.replace('_', ' ').title()}</span>
        </div>
        <div class="diag-card">
          <span class="diag-label">Title Length</span>
          <span class="diag-value">{ds.density.title_length}</span>
        </div>
        <div class="diag-card">
          <span class="diag-label">Templates</span>
          <span class="diag-value">{result.templates_considered} total &rarr; {result.templates_after_filter} filtered &rarr; {result.templates_after_z3} after Z3</span>
        </div>
        <div class="diag-card">
          <span class="diag-label">Candidates Rendered</span>
          <span class="diag-value">{len(result.rendered_paths)}</span>
        </div>
      </div>
    </div>"""

    reasoning_html = ""
    if result.reasoning:
        reasoning_html = f'<div class="reasoning">{result.reasoning}</div>'

    cards = []
    for i, path in enumerate(result.rendered_paths):
        layout = result.layouts[i]
        is_best = i == result.best_index
        winner_class = " winner" if is_best else ""
        best_badge = '<span class="best-label">BEST</span>' if is_best else ""
        typo_str = ", ".join(f"{k}: {v}px" for k, v in layout.typography.font_sizes.items())
        cards.append(f"""
        <div class="card{winner_class}">
          {best_badge}
          <img src="/output/{path.name}" alt="{layout.template.label}">
          <div class="card-info">
            <h3>{layout.template.label}</h3>
            <span class="score">Score: {layout.heuristic_score:.2f}</span>
            <span class="typo">{typo_str}</span>
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Runeform — Results</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f8f4ee;
    color: #333;
    min-height: 100vh;
    padding: 40px 20px;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .back {{ color: #888; text-decoration: none; font-size: 0.85rem; }}
  .back:hover {{ text-decoration: underline; }}
  .meta {{ color: #888; margin-bottom: 20px; font-size: 0.85rem; }}
  .diag {{ background: white; padding: 20px 24px; border-radius: 10px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  .diag h3 {{ font-size: 0.85rem; color: #888; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .diag-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
  .diag-card {{ background: #f8f4ee; padding: 10px 14px; border-radius: 8px; }}
  .diag-label {{ display: block; font-size: 0.75rem; color: #999; margin-bottom: 2px; }}
  .diag-value {{ font-weight: 600; font-size: 0.9rem; }}
  .reasoning {{ background: white; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px; font-size: 0.9rem; color: #555; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  .best-label {{ display: inline-block; background: #333; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
  .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); cursor: pointer; transition: transform 0.15s; }}
  .card:hover {{ transform: translateY(-2px); }}
  .card.winner {{ outline: 3px solid #333; box-shadow: 0 4px 20px rgba(0,0,0,0.12); }}
  .card img {{ width: 100%; display: block; }}
  .card-info {{ padding: 12px 16px; }}
  .card-info h3 {{ font-size: 0.9rem; margin-bottom: 4px; }}
  .card-info .score {{ color: #999; font-size: 0.8rem; display: block; }}
  .card-info .typo {{ color: #bbb; font-size: 0.75rem; display: block; margin-top: 2px; }}
  .modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 100; align-items: center; justify-content: center; }}
  .modal.open {{ display: flex; }}
  .modal img {{ max-width: 90vw; max-height: 90vh; border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.4); }}
</style>
</head>
<body>
<div class="container">
  <a href="/" class="back">&larr; New generation</a>
  <h1>Generated Layouts</h1>
  <p class="meta">{len(result.rendered_paths)} variants generated</p>
  {diag}
  {reasoning_html}
  <div class="grid">
  {"".join(cards)}
  </div>
</div>
<div class="modal" id="modal" onclick="this.classList.remove('open')">
  <img id="modal-img" src="" alt="Layout close-up">
</div>
<script>
document.querySelectorAll('.card img').forEach(img => {{
  img.addEventListener('click', () => {{
    document.getElementById('modal-img').src = img.src;
    document.getElementById('modal').classList.add('open');
  }});
}});
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') document.getElementById('modal').classList.remove('open');
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/generate")
async def api_generate(
    title: str = Form(...),
    date: str = Form(default=""),
    time: str = Form(default=""),
    location: str = Form(default=""),
    description: str = Form(default=""),
    image: UploadFile | None = File(default=None),
    brand_zip: UploadFile | None = File(default=None),
    max_solutions: int = Form(default=3),
):
    title = title.strip()
    if not title:
        return {"error": "Title is required"}

    image_path = None
    if image and image.filename and image.size and image.size > 0:
        UPLOADS_DIR.mkdir(exist_ok=True)
        image_path = UPLOADS_DIR / image.filename
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)

    brand_kit = None
    if brand_zip and brand_zip.filename and brand_zip.size and brand_zip.size > 0:
        zip_bytes = await brand_zip.read()
        brand_kit, _ = import_zip(zip_bytes)
        save_brand(brand_kit, _)
    else:
        loaded = load_brand()
        if loaded:
            brand_kit, _ = loaded

    event = EventData(
        title=title,
        date=date.strip() or None,
        time=time.strip() or None,
        location=location.strip() or None,
        description=description.strip() or None,
        image_path=image_path,
    )

    result = generate(event, brand=brand_kit, max_typo_solutions=max_solutions)

    return {
        "data_shape": {
            "content_type": result.data_shape.content_type.value,
            "density": result.data_shape.density.model_dump(),
        },
        "templates_considered": result.templates_considered,
        "templates_after_filter": result.templates_after_filter,
        "templates_after_z3": result.templates_after_z3,
        "best_index": result.best_index,
        "reasoning": result.reasoning,
        "layouts": [
            {
                "template": layout.template.name,
                "label": layout.template.label,
                "score": layout.heuristic_score,
                "typography": layout.typography.font_sizes,
                "image": f"/output/{path.name}",
            }
            for layout, path in zip(result.layouts, result.rendered_paths)
        ],
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    return _generate_form_html()


@app.post("/generate", response_class=HTMLResponse)
async def do_generate(
    title: str = Form(...),
    date: str = Form(default=""),
    time: str = Form(default=""),
    location: str = Form(default=""),
    description: str = Form(default=""),
    image: UploadFile | None = File(default=None),
):
    title = title.strip()
    if not title:
        return HTMLResponse(
            "<p>Title is required.</p><a href='/'>Back</a>",
            status_code=400,
        )

    image_path = None
    if image and image.filename and image.size and image.size > 0:
        UPLOADS_DIR.mkdir(exist_ok=True)
        image_path = UPLOADS_DIR / image.filename
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)

    # Load brand kit if configured
    brand_kit = None
    loaded = load_brand()
    if loaded:
        brand_kit, _ = loaded

    event = EventData(
        title=title,
        date=date.strip() or None,
        time=time.strip() or None,
        location=location.strip() or None,
        description=description.strip() or None,
        image_path=image_path,
    )

    result = generate(event, brand=brand_kit)

    if not result.layouts:
        return HTMLResponse(
            f"<p>Could not generate any layouts for this content. "
            f"Data shape: {result.data_shape.content_type.value}. "
            f"Try a shorter title or fewer details.</p>"
            f"<a href='/'>Back</a>",
            status_code=200,
        )

    return HTMLResponse(_results_html(result))


# ---------------------------------------------------------------------------
# Brand Kit routes
# ---------------------------------------------------------------------------

@app.get("/brand", response_class=HTMLResponse)
async def brand_page():
    loaded = load_brand()
    if loaded:
        brand, logo_path = loaded
        return _brand_form_html(brand, logo_path)
    return _brand_form_html()


@app.post("/brand", response_class=HTMLResponse)
async def save_brand_form(
    brand_name: str = Form(...),
    address: str = Form(default=""),
    color1: str = Form(default="#333333"),
    color2: str = Form(default="#888888"),
    color3: str = Form(default="#f8f4ee"),
    brand_description: str = Form(default=""),
    logo: UploadFile | None = File(default=None),
):
    brand = BrandKit(
        name=brand_name.strip(),
        address=address.strip(),
        description=brand_description.strip(),
        colors=[color1, color2, color3],
    )

    logo_path = None
    if logo and logo.filename and logo.size and logo.size > 0:
        UPLOADS_DIR.mkdir(exist_ok=True)
        logo_path = UPLOADS_DIR / f"brand_logo{Path(logo.filename).suffix}"
        with open(logo_path, "wb") as f:
            content = await logo.read()
            f.write(content)
    else:
        # Preserve existing logo if user didn't upload a new one
        existing = load_brand()
        if existing:
            old_brand, old_logo = existing
            if old_brand.logo_filename:
                brand.logo_filename = old_brand.logo_filename

    save_brand(brand, logo_path)

    # Reload to get the saved state
    loaded = load_brand()
    brand, saved_logo = loaded
    return _brand_form_html(brand, saved_logo, message="Brand kit saved.")


@app.get("/brand/export")
async def export_brand():
    loaded = load_brand()
    if not loaded:
        return HTMLResponse("<p>No brand kit configured.</p><a href='/brand'>Set up brand</a>", status_code=404)

    brand, logo_path = loaded
    buf = export_zip(brand, logo_path)

    filename = brand.name.lower().replace(" ", "_") + "_brand.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/brand/import", response_class=HTMLResponse)
async def import_brand(
    brand_zip: UploadFile = File(...),
):
    zip_bytes = await brand_zip.read()
    brand, logo_path = import_zip(zip_bytes)
    save_brand(brand, logo_path)

    loaded = load_brand()
    brand, saved_logo = loaded
    return _brand_form_html(brand, saved_logo, message=f"Imported brand kit: {brand.name}")


@app.get("/brand-logo")
async def brand_logo():
    loaded = load_brand()
    if loaded:
        _, logo_path = loaded
        if logo_path and logo_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(logo_path)
    return HTMLResponse("", status_code=404)
