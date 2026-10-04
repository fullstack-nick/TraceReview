"""Test-only server. A new isolated file database per invocation; no personal data."""
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["TRACEREVIEW_DB"] = str(ROOT / ".local" / f"e2e-{uuid.uuid4().hex}.sqlite3")
dev = os.environ.get("TRACEREVIEW_E2E_MODE") == "dev"
os.environ["TRACEREVIEW_DEBUG"] = "1" if dev else "0"
import django
django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command
call_command("migrate", interactive=False, verbosity=0)
get_user_model().objects.create_user("analyst", password="Test-only-analysis-791!")
get_user_model().objects.create_user("other-analyst", password="Test-only-secondary-682!")
if dev:
    call_command("runserver", "127.0.0.1:8001", use_reloader=False)
else:
    from config.wsgi import application
    from waitress import serve
    serve(application, host="127.0.0.1", port=8001, threads=4, max_request_body_size=524288)
