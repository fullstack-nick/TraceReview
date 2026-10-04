"""Generate original synthetic fixtures; committed bytes are the canonical inputs."""
from pathlib import Path
import hashlib
import math

ROOT = Path(__file__).resolve().parent
files = {
    "triangle.csv": "time_min,signal_au\n0,0\n1,2\n2,0\n",
    "irregular.csv": "time_min,signal_au\n0,0\n1,2\n3,2\n4,0\n",
    "invalid-duplicate-time.csv": "time_min,signal_au\n0,0\n1,2\n1,1\n2,0\n",
}
for name, amplitude, center, width in [
    ("clean-trace.csv", .12, 7., .2),
    ("neighboring-feature.csv", .30, 5.35, .25),
]:
    lines = ["time_min,signal_au"]
    for i in range(601):
        t = i / 60
        y = math.exp(-.5 * ((t - 4.5) / .45) ** 2) + amplitude * math.exp(-.5 * ((t - center) / width) ** 2)
        lines.append(f"{t:.17g},{y:.17g}")
    files[name] = "\n".join(lines) + "\n"
for name, content in files.items():
    (ROOT / name).write_bytes(content.encode("utf-8"))
rows = [f"| `{name}` | `{hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}` |" for name in sorted(files)]
(ROOT / "README.md").write_text(
    "# Synthetic fixtures\n\nOriginal deterministic curves; no instrument or biological data. MIT licensed. "
    "Run `uv run python fixtures/generate.py` to regenerate. UTF-8, LF, 17 significant digits.\n\n"
    "The two demonstration traces have 601 points across 0–10 min. Both contain "
    "exp(-0.5*((t-4.5)/0.45)^2). The clean trace adds a 0.12-amplitude feature at 7 min "
    "(width 0.2); the neighboring trace adds a 0.30-amplitude feature at 5.35 min (width 0.25).\n\n"
    "Triangle: total 2; [0.5,1.5] area 1.5, fraction 75%. Irregular: total 6; [0.5,3.5] area 5.5. "
    "The invalid file must reject duplicate time on line 4.\n\n"
    "| File | SHA-256 |\n|---|---|\n" + "\n".join(rows) + "\n", encoding="utf-8", newline="\n")
print(f"Generated {len(files)} synthetic fixtures.")
