import os
import struct
import tempfile
import uuid
from flask import Flask, request, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_DIR = tempfile.mkdtemp(prefix="upload_")

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DocuFlow — Free Online PDF Tools</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%232563eb'/%3E%3Cpath d='M9 8h6a5 5 0 0 1 0 10H9V8zm0 0v16' stroke='white' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f1f5f9;
    color: #0f172a;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
  }
  .nav {
    max-width: 1080px;
    margin: 0 auto;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 28px;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 1.2em;
    font-weight: 700;
    color: #0f172a;
    text-decoration: none;
  }
  .logo-mark {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: #2563eb;
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85em;
    font-weight: 800;
  }
  .nav-links {
    display: flex;
    gap: 22px;
    margin-left: 12px;
  }
  .nav-links a {
    color: #475569;
    text-decoration: none;
    font-size: 0.92em;
  }
  .nav-links a:hover { color: #0f172a; }
  .nav-cta {
    margin-left: auto;
    background: #2563eb;
    color: #fff;
    border: none;
    padding: 9px 20px;
    border-radius: 8px;
    font-size: 0.9em;
    font-weight: 600;
    cursor: pointer;
  }
  .nav-cta:hover { background: #1d4ed8; }
  main {
    flex: 1;
    width: 100%;
    max-width: 1080px;
    margin: 0 auto;
    padding: 56px 24px 40px;
  }
  .hero { text-align: center; max-width: 640px; margin: 0 auto; }
  .hero h1 { font-size: 2.3em; letter-spacing: -0.02em; margin-bottom: 12px; }
  .hero p { color: #475569; font-size: 1.05em; margin-bottom: 28px; }
  .card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 32px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    text-align: left;
  }
  .drop {
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
    padding: 34px 20px;
    text-align: center;
    margin-bottom: 18px;
    background: #f8fafc;
  }
  .drop:hover { border-color: #2563eb; }
  .drop p { color: #64748b; font-size: 0.9em; margin-top: 10px; }
  input[type="file"] {
    font-family: inherit;
    font-size: 0.92em;
    color: #334155;
  }
  .btn {
    background: #2563eb;
    color: #ffffff;
    border: none;
    padding: 13px 30px;
    font-size: 1em;
    font-weight: 600;
    border-radius: 9px;
    cursor: pointer;
    width: 100%;
  }
  .btn:hover { background: #1d4ed8; }
  .report {
    margin-top: 20px;
    padding: 16px 18px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 9px;
    white-space: pre-wrap;
    font-size: 0.9em;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    max-height: 260px;
    overflow-y: auto;
  }
  .report.error {
    background: #fef2f2;
    border-color: #fecaca;
    color: #991b1b;
  }
  .report.ok { color: #166534; border-color: #bbf7d0; background: #f0fdf4; }
  .trust {
    display: flex;
    justify-content: center;
    gap: 26px;
    margin: 26px 0 54px;
    color: #64748b;
    font-size: 0.88em;
    flex-wrap: wrap;
  }
  .features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
  }
  .feature {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 22px;
  }
  .feature h3 { font-size: 1em; margin-bottom: 8px; }
  .feature p { color: #64748b; font-size: 0.88em; line-height: 1.55; }
  footer {
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    margin-top: auto;
  }
  .foot {
    max-width: 1080px;
    margin: 0 auto;
    padding: 22px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    color: #94a3b8;
    font-size: 0.82em;
    flex-wrap: wrap;
  }
  .foot nav { display: flex; gap: 18px; margin-left: auto; }
  .foot a { color: #94a3b8; text-decoration: none; }
  .foot a:hover { color: #475569; }
</style>
</head>
<body>
<header>
  <div class="nav">
    <a class="logo" href="/"><span class="logo-mark">D</span>DocuFlow</a>
    <div class="nav-links">
      <a href="#">Tools</a>
      <a href="#">Compress</a>
      <a href="#">Convert</a>
      <a href="#">Pricing</a>
    </div>
    <button class="nav-cta" type="button">Sign in</button>
  </div>
</header>
<main>
  <div class="hero">
    <h1>Process PDFs online, free</h1>
    <p>Upload a document and get a page-by-page processing report in seconds. No sign-up required.</p>
    <div class="card">
      <form method="POST" enctype="multipart/form-data">
        <div class="drop">
          <input type="file" name="pdf" accept=".pdf,application/pdf">
          <p>Drop a PDF here or click to browse — max 5 MB</p>
        </div>
        <button class="btn" type="submit">Process now</button>
      </form>
      {% if result %}
      <div class="report {{ 'error' if error else 'ok' }}">{{ result }}</div>
      {% endif %}
    </div>
    <div class="trust">
      <span>Free for basic use</span>
      <span>No account needed</span>
      <span>Files deleted after processing</span>
    </div>
  </div>
  <div class="features">
    <div class="feature">
      <h3>Fast processing</h3>
      <p>Documents are handled instantly on our servers with per-page status reporting.</p>
    </div>
    <div class="feature">
      <h3>Private by design</h3>
      <p>Uploads are removed from our servers as soon as your report is ready.</p>
    </div>
    <div class="feature">
      <h3>Works anywhere</h3>
      <p>Runs in any modern browser on desktop or mobile. Nothing to install.</p>
    </div>
  </div>
</main>
<footer>
  <div class="foot">
    <span>&copy; 2026 DocuFlow · v2.4.1</span>
    <nav>
      <a href="#">Privacy</a>
      <a href="#">Terms</a>
      <a href="#">Contact</a>
      <a href="#">API</a>
    </nav>
  </div>
</footer>
</body>
</html>
"""


def process_pdf(filepath):
    import pymupdf

    doc = pymupdf.open(filepath)
    results = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        xref = page.xref

        raw = doc.xref_get_key(xref, "DocMeta")
        if raw[0] == "null":
            results.append(f"Page {page_num + 1}: no data")
            continue

        flat_bits = [int(v) for v in raw[1].strip("[]").split()]
        if len(flat_bits) % 2 != 0:
            results.append(f"Page {page_num + 1}: invalid entry")
            continue

        pts = []
        for i in range(0, len(flat_bits), 2):
            lo_bits = flat_bits[i]
            hi_bits = flat_bits[i + 1]
            x = struct.unpack("<f", struct.pack("<I", lo_bits & 0xFFFFFFFF))[0]
            y = struct.unpack("<f", struct.pack("<I", hi_bits & 0xFFFFFFFF))[0]
            pts.append((x, y))

        results.append(f"Page {page_num + 1}: processing...")

        rect = pymupdf.Rect(50, 50, 200, 150)
        page.add_freetext_annot(rect, "processed", callout=pts)
        results.append(f"Page {page_num + 1}: done")

    doc.close()
    return "\n".join(results)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = False

    if request.method == "POST":
        f = request.files.get("pdf")
        if not f or not f.filename:
            result = "Error: no file uploaded"
            error = True
        elif not f.filename.lower().endswith(".pdf"):
            result = "Error: only .pdf files accepted"
            error = True
        else:
            path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.pdf")
            f.save(path)
            try:
                result = process_pdf(path)
            except Exception:
                result = "Processing failed"
                error = True
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    return render_template_string(HTML, result=result, error=error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
