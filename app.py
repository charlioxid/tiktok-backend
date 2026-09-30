import os, re, shutil, tempfile
from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import yt_dlp

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
CORS(app)  # পরে "*" এর বদলে নিজের সাইটের ঠিকানা দিন
limiter = Limiter(get_remote_address, app=app,
                  default_limits=["60 per hour"])

URL_RE = re.compile(r"^https?://([a-z0-9-]+\.)?tiktok\.com/", re.I)
MAX_SIZE = 50 * 1024 * 1024  # 50MB

@app.route("/")
def home():
    return "Server is running"

@app.route("/download")
@limiter.limit("5 per minute")
def download():
    url = request.args.get("url", "").strip()
    if not URL_RE.match(url):
        return jsonify(error="Invalid TikTok link"), 400

    tmp = tempfile.mkdtemp()
    opts = {
        "outtmpl": os.path.join(tmp, "video.%(ext)s"),
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "max_filesize": MAX_SIZE,
        "socket_timeout": 20,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = os.listdir(tmp)
        if not files:
            raise Exception("no file")
        path = os.path.join(tmp, files[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return jsonify(error="Download failed"), 500

    @after_this_request
    def cleanup(resp):
        shutil.rmtree(tmp, ignore_errors=True)
        return resp

    return send_file(path, as_attachment=True,
                     download_name="tiktok_video.mp4")
