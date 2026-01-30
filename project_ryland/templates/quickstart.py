import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def create_quickstart(dest: str, overwrite: bool = False):
    """
    Copies the quickstart template files to the user's desired directory.

    Args:
        dest (str): Path to the destination directory.
        overwrite (bool): Whether to overwrite existing files.
    """
    dest_path = Path(dest).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[INFO] Creating quickstart project at: {dest_path}")

    # Locate the package's template folder
    try:
        import importlib.resources as pkg_resources
        from . import data
        template_dir = Path(pkg_resources.files(data))
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