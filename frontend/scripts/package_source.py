"""Offer this build's corresponding frontend source without deployment secrets.

Run after `npm run build`: python scripts/package_source.py
The public archive deliberately contains only the frontend allowlist below.
"""
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
target = root / "dist/assets/source/personalrag-frontend-source.zip"
entries = ["src", "public", "scripts", "tests", "index.html", "package.json",
           "package-lock.json", "vite.config.js", "jsconfig.json", "README.md",
           "THIRD_PARTY_NOTICES.md"]
files = []
for entry in entries:
    path = root / entry
    for file in sorted(path.rglob("*") if path.is_dir() else [path]):
        relative = file.relative_to(root)
        if file.is_file() and not any(part.startswith(".") or part in ("__pycache__", "node_modules", "dist", "source") for part in relative.parts):
            files.append((file, relative))
target.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for file, relative in files:
        archive.write(file, "personalrag-frontend/" + relative.as_posix())
print(f"Frontend source: {len(files)} files, {target.stat().st_size} bytes")

# A content-hashed source URL avoids a stale fixed-name ZIP at CDN edges.
entry = (root / "dist/index.html").read_text(encoding="utf-8")
match = re.search(r'src="/assets/(index-[^"/]+)\.js"', entry)
if not match:
    raise RuntimeError("Cannot identify the built frontend entry for source versioning")
versioned = target.with_name(f"personalrag-frontend-source-{match.group(1)}.zip")
shutil.copyfile(target, versioned)
print(f"Versioned source: {versioned.name}")
