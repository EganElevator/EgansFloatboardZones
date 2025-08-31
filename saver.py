import os
import json
from pathlib import Path
from PyQt6.QtGui import QColor

# Path for saving
APP_FOLDER = Path.home() / "AppData" / "Local" / "EgansFloatboard" / "Zones"
APP_FOLDER.mkdir(parents=True, exist_ok=True)
GLOBAL_CONFIG_FILE = APP_FOLDER / "global_config.json"

# Defaults for zones and global
DEFAULT_GLOBALS = {
    "rows": 5, "cols": 4, "cell_icon_size": 48, "text_size": 10,
    "title_text_size": 14, "title_height": 28, "label_height": 16,
    "scale_offset_x": 1, "scale_offset_y": 1,
    "bg_color": "#323232", "name_color": "#ffffff", "title_bg": "#9f00f0", "title_text": "#ffffff"
}

def save_zone_config(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    zone_name = getattr(zone, "title_bar", None)
    name = zone_name.text() if zone_name else "zone"
    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:60] or "zone"
    data = {
        "zone_name": name,
        "folder": getattr(zone, "folder", ""),
        "rows": zone.rows,
        "cols": zone.cols,
        "cell_icon_size": zone.cell_icon_size,
        "text_size": zone.text_size,
        "title_text_size": zone.title_text_size,
        "title_height": zone.title_height,
        "label_height": zone.label_height,
        "scale_offset_x": zone.scale_offset_x,
        "scale_offset_y": zone.scale_offset_y,
        "bg_color": zone.bg_color.name(),
        "name_color": zone.name_color.name(),
        "title_bg": zone.title_bg.name(),
        "title_text": zone.title_text.name(),
        "local_overrides": list(getattr(zone, "local_overrides", [])),
        "geometry": list(zone.geometry().getRect())
    }
    path = APP_FOLDER / f"{safe}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def save_global_config(app):
    data = {}
    for key in DEFAULT_GLOBALS.keys():
        val = getattr(app, key, None)
        if isinstance(val, QColor):
            data[key] = val.name()
        else:
            data[key] = val
    with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_global_config():
    if GLOBAL_CONFIG_FILE.exists():
        with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_GLOBALS.copy()

def load_zone_files():
    zones = []
    for p in APP_FOLDER.glob("*.json"):
        if p.name == GLOBAL_CONFIG_FILE.name:
            continue
        with open(p, "r", encoding="utf-8") as f:
            zones.append(json.load(f))
    return zones
