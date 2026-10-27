import io
import re
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from mesh_converter import export_obj, read_vessels


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/convert")
def convert():
    uploaded_file = request.files.get("xml_file")
    if uploaded_file is None or not uploaded_file.filename:
        return render_template("index.html", error="Choose a Neurolucida XML file to convert."), 400
    if Path(uploaded_file.filename).suffix.lower() != ".xml":
        return render_template("index.html", error="The uploaded file must have an .xml extension."), 400

    try:
        radial_segments = int(request.form.get("radial_segments", "8"))
        vessels = read_vessels(uploaded_file.stream)
        obj_text, mtl_text = export_obj(vessels, radial_segments=radial_segments)
    except (ValueError, UnicodeDecodeError) as exc:
        return render_template("index.html", error=str(exc)), 400

    base_name = Path(secure_filename(uploaded_file.filename)).stem or "neurolucida_vessels"
    base_name = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name).strip("_") or "neurolucida_vessels"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr(f"{base_name}.obj", obj_text)
        output.writestr("vessels.mtl", mtl_text)
    archive.seek(0)
    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{base_name}_mesh.zip",
    )


@app.errorhandler(413)
def file_too_large(_error):
    return render_template("index.html", error="The XML file exceeds the 50 MB upload limit."), 413


if __name__ == "__main__":
    app.run(debug=False)
