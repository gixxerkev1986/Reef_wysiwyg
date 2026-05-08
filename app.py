import os
import json
import zipfile
from datetime import datetime
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ALBUMS_FILE = os.path.join(BASE_DIR, "albums.json")

WHATSAPP_NUMBER = "31600000000"  # aanpassen naar jouw nummer zonder +

os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(ALBUMS_FILE):
    with open(ALBUMS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


def load_albums():
    with open(ALBUMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_albums(data):
    with open(ALBUMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def resize_image(src, dst, max_size):
    with Image.open(src) as img:
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        img.save(dst, "JPEG", quality=82, optimize=True)


@app.route("/")
def home():
    return redirect(url_for("admin"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        album_name = request.form.get("album_name", "").strip()
        prefix = request.form.get("prefix", "SPS").strip().upper()
        zip_file = request.files.get("zip_file")

        if not album_name or not zip_file:
            return "Albumnaam en ZIP-bestand zijn verplicht."

        slug = secure_filename(album_name.lower().replace(" ", "-"))
        album_dir = os.path.join(UPLOAD_DIR, slug)
        original_dir = os.path.join(album_dir, "originals")
        web_dir = os.path.join(album_dir, "web")
        thumb_dir = os.path.join(album_dir, "thumbs")

        os.makedirs(original_dir, exist_ok=True)
        os.makedirs(web_dir, exist_ok=True)
        os.makedirs(thumb_dir, exist_ok=True)

        zip_path = os.path.join(album_dir, "upload.zip")
        zip_file.save(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(original_dir)

        images = []
        count = 1

        for root, dirs, files in os.walk(original_dir):
            for filename in sorted(files):
                if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    src = os.path.join(root, filename)
                    code = f"{prefix}-{count:03d}"

                    web_filename = f"{code}.jpg"
                    thumb_filename = f"{code}.jpg"

                    web_path = os.path.join(web_dir, web_filename)
                    thumb_path = os.path.join(thumb_dir, thumb_filename)

                    resize_image(src, web_path, 1600)
                    resize_image(src, thumb_path, 500)

                    images.append({
                        "code": code,
                        "web": f"{slug}/web/{web_filename}",
                        "thumb": f"{slug}/thumbs/{thumb_filename}",
                        "status": "beschikbaar"
                    })

                    count += 1

        albums = load_albums()
        albums[slug] = {
            "name": album_name,
            "prefix": prefix,
            "created_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "images": images
        }
        save_albums(albums)

        return redirect(url_for("gallery", slug=slug))

    albums = load_albums()
    return render_template("admin.html", albums=albums)


@app.route("/gallery/<slug>")
def gallery(slug):
    albums = load_albums()
    album = albums.get(slug)

    if not album:
        return "Album niet gevonden."

    return render_template(
        "gallery.html",
        album=album,
        slug=slug,
        whatsapp_number=WHATSAPP_NUMBER
    )


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
