"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Institution:    Dana-Farber Cancer Institute
Working Groups: Lindvall & Rhee Labs
Parent Package: Project Ryland
Creation Date:  2026.01.29
Last Modified:  2026.01.29

Purpose:
Allow the user to quickly download the folder with template files and
data using a python import
------------------------------------------------------------------------------
"""

import importlib.resources as pkg_resources
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

def create_quickstart(dest: str, overwrite: bool = False):
    dest_path = Path(dest).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[INFO] Creating quickstart project at: {dest_path}")

    # Locate the package's quickstart template folder
    try:
        import project_ryland.templates.quickstart as qs_pkg
        # This gets the folder path of the quickstart package
        template_dir = Path(pkg_resources.files(qs_pkg))
    except Exception as e:
        raise RuntimeError(f"[ERROR] Could not locate template directory: {e}")

    # Copy all files from template_dir to dest_path
    for item in template_dir.iterdir():
        target = dest_path / item.name
        if target.exists() and not overwrite:
            logger.warning(f"[WARNING] File already exists and will be skipped: {target}")
            continue
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=overwrite)
        else:
            shutil.copy2(item, target)
        logger.info(f"[INFO] Copied: {item.name}")

    print(f"[SUCCESS] Quickstart template created at {dest_path}")