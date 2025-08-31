import os
import json
from pathlib import Path

APP_FOLDER = Path.home() / "AppData" / "Local" / "EgansFloatboard" / "Zones"
APP_FOLDER.mkdir(parents=True, exist_ok=True)

GLOBAL_CONFIG_FILE = os.path.join(APP_FOLDER, "global_config.json")


def get_zone_file(zone):
    """Return the path for saving a zone config by its zone name."""
    safe_name = f"{zone.zone_name}.json"
    return os.path.join(APP_FOLDER, safe_name)


def save_zone_config(zone):
    """Save a zone’s configuration into its own JSON file."""
    data = {
        "zone_name": getattr(zone, "zone_name", "Unnamed"),
        "path": getattr(zone, "folder_path", ""),
        "rows": zone.rows,
        "cols": zone.cols,
        "scale_offset_x": zone.scale_offset_x,
        "scale_offset_y": zone.scale_offset_y,
        "text_size": zone.text_size,
        "title_text_size": zone.title_text_size,
        "bg_color": str(zone.bg_color.name() if hasattr(zone.bg_color, "name") else zone.bg_color),
        "name_color": str(zone.name_color.name() if hasattr(zone.name_color, "name") else zone.name_color),
        "title_bg": str(zone.title_bg.name() if hasattr(zone.title_bg, "name") else zone.title_bg),
        "title_text": str(zone.title_text.name() if hasattr(zone.title_text, "name") else zone.title_text),
        "overrides": list(getattr(zone, "local_overrides", []))
    }

    with open(get_zone_file(zone), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_global_config(app):
    """Save the global configuration (from TrayApp) into global_config.json."""
    data = {
        "rows": app.rows,
        "cols": app.cols,
        "scale_offset_x": app.scale_offset_x,
        "scale_offset_y": app.scale_offset_y,
        "text_size": app.text_size,
        "title_text_size": app.title_text_size,
        "bg_color": str(app.bg_color.name() if hasattr(app.bg_color, "name") else app.bg_color),
        "name_color": str(app.name_color.name() if hasattr(app.name_color, "name") else app.name_color),
        "title_bg": str(app.title_bg.name() if hasattr(app.title_bg, "name") else app.title_bg),
        "title_text": str(app.title_text.name() if hasattr(app.title_text, "name") else app.title_text)
    }

    with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
