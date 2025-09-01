from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict
from PyQt6.QtGui import QColor

# Root: %LOCALAPPDATA%/EgansFloatboard/Zones  (fallback: HOME)
BASE_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "EgansFloatboard" / "Zones"
ZONES_DIR = BASE_DIR / "Zones"
SETTINGS_DIR = BASE_DIR / "Settings"
GLOBAL_CONFIG_FILE = SETTINGS_DIR / "global_config.json"

DEFAULT_GLOBALS: Dict[str, Any] = {
    "rows": 5,
    "cols": 4,
    "cell_icon_size": 48,
    "text_size": 10,
    "title_text_size": 14,
    "title_height": 28,
    "label_height": 16,
    "scale_offset_x": 1,
    "scale_offset_y": 1,
    "bg_color": "#323232",
    "name_color": "#ffffff",
    "title_bg": "#9f00f0",
    "title_text": "#ffffff",
}

# Ensure folders exist
for d in (ZONES_DIR, SETTINGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

def _serialize(v: Any) -> Any:
    return v.name() if isinstance(v, QColor) else v

def safe_name(name: str) -> str:
    s = "".join(c for c in (name or "") if c.isalnum() or c in "-_ ").strip()
    s = s.replace(" ", "_")
    return (s or "Zone")[:60]

def save_zone_config(zone_or_dict) -> Path:
    """Accepts a Zone instance (preferred) or a dict from Zone.to_dict()."""
    data = zone_or_dict.to_dict() if hasattr(zone_or_dict, "to_dict") else dict(zone_or_dict)
    name = data.get("zone_name") or "Zone"
    path = ZONES_DIR / f"{safe_name(name)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

def load_zone_files() -> list[Dict[str, Any]]:
    zones: list[Dict[str, Any]] = []
    for p in ZONES_DIR.glob("*.json"):
        if p.name.lower() == GLOBAL_CONFIG_FILE.name.lower():
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                zones.append(json.load(f))
        except Exception:
            pass
    return zones

def load_global_config() -> Dict[str, Any]:
    if GLOBAL_CONFIG_FILE.exists():
        try:
            with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_GLOBALS.copy()

def save_global_config(app_or_dict) -> Path:
    if isinstance(app_or_dict, dict):
        data = app_or_dict
    else:
        data = {k: _serialize(getattr(app_or_dict, k, DEFAULT_GLOBALS[k])) for k in DEFAULT_GLOBALS}
    with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return GLOBAL_CONFIG_FILE
