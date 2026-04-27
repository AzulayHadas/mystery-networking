#!/usr/bin/env python3
"""
Builds the livedemo/ folder as a self-contained, customer-ready package.
Run once from the repo root:   python build_livedemo.py
"""
import shutil
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(ROOT, "livedemo")


def clean():
    """Remove previous build (keep setup_demo.py if manually edited)."""
    for item in ["backend", "frontend"]:
        p = os.path.join(DEST, item)
        if os.path.exists(p):
            shutil.rmtree(p)


def copy_backend():
    dest = os.path.join(DEST, "backend")
    os.makedirs(dest, exist_ok=True)
    for f in ["app.py", "models.py", "scoring.py", "requirements.txt"]:
        src = os.path.join(ROOT, "backend", f)
        if os.path.exists(src):
            shutil.copy2(src, dest)
    print(f"  ✅ backend/  ({len(os.listdir(dest))} files)")


def copy_frontend():
    src = os.path.join(ROOT, "frontend")
    dest = os.path.join(DEST, "frontend")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    count = sum(len(files) for _, _, files in os.walk(dest))
    print(f"  ✅ frontend/ ({count} files)")


def main():
    print("🔨 Building livedemo/ ...")
    clean()
    copy_backend()
    copy_frontend()
    print()
    print("Done.  To run the demo:")
    print("  cd livedemo")
    print("  pip install -r backend/requirements.txt")
    print("  python setup_demo.py")


if __name__ == "__main__":
    main()
