import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["TRACEREVIEW_DEBUG"] = "0"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not (ROOT / "frontend/dist/index.html").exists() or not (ROOT / ".local/static/app/index.html").exists():
        raise SystemExit("Build missing. Run scripts/build.ps1 first.")
    from config.wsgi import application
    from waitress import serve
    print(f"TraceReview: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
    serve(application, host="127.0.0.1", port=args.port, threads=4, max_request_body_size=524288)
