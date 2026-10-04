import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from review.provenance import build_metadata

(ROOT / ".local/build.json").write_text(json.dumps(build_metadata(), indent=2) + "\n", encoding="utf-8")
print("Build provenance saved to .local/build.json.")
