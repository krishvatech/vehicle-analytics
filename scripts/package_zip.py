"""Package the entire repository into a zip archive.

Usage:
    python scripts/package_zip.py

This script creates a ZIP file under ``dist/`` named
``cctv-vehicle-analytics.zip`` containing all files in the project
directory.  The zip file can be provided as the final deliverable.
"""

import os
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'dist')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'cctv-vehicle-analytics.zip')


def zipdir(path: str, ziph: zipfile.ZipFile) -> None:
    """Recursively add a directory to a zip archive."""
    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            # Skip the dist folder itself
            if '/dist/' in filepath:
                continue
            arcname = os.path.relpath(filepath, start=ROOT_DIR)
            ziph.write(filepath, arcname)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with zipfile.ZipFile(OUTPUT_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir(ROOT_DIR, zipf)
    print(f"Created archive at {OUTPUT_FILE}")


if __name__ == '__main__':
    main()