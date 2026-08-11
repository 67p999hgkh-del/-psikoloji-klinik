"""
GoDaddy / cPanel Passenger giriş noktası.
Setup Python App → Application startup file: passenger_wsgi.py
Entry point: application
"""
import os
import sys
import traceback

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

os.chdir(APP_ROOT)
os.makedirs(os.path.join(APP_ROOT, "instance"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "tmp"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT, "static", "uploads", "therapists"), exist_ok=True)

try:
    from app import app as application
except Exception:
    # Passenger 500 yerine hatayı HTML olarak göster (kurulum sırasında teşhis için)
    _error = traceback.format_exc()

    def application(environ, start_response):
        body = (
            "<h1>Uygulama başlatılamadı</h1>"
            "<p>Aşağıdaki hatayı kopyalayıp destek / geliştiriciye gönderin:</p>"
            "<pre style='white-space:pre-wrap;background:#111;color:#eee;padding:1rem'>"
            + _error
            + "</pre>"
        ).encode("utf-8")
        start_response(
            "500 Internal Server Error",
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
        )
        return [body]
