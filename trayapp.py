import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QRect

from zone import Zone
from saver import APP_FOLDER, ZONES_DIR, SETTINGS_DIR, save_global_config


class TrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        # Ensure config dirs exist
        APP_FOLDER.mkdir(parents=True, exist_ok=True)
        ZONES_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Global config path
        self.CONFIG_FILE = SETTINGS_DIR / "global_config.json"

        # Load or create global config
        self.global_config = self._load_global()

        # Zones
        self.zones = []
        self._load_saved_zones()

        # Tray icon
        self.tray = QSystemTrayIcon(QIcon.fromTheme("folder"), self)
        self.menu = QMenu()

        add_zone_action = QAction("Add Zone", self)
        add_zone_action.triggered.connect(self.add_zone)
        self.menu.addAction(add_zone_action)

        global_customize_action = QAction("Global Settings", self)
        global_customize_action.triggered.connect(self.global_customize)
        self.menu.addAction(global_customize_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

    # ------------------------
    # Config management
    # ------------------------
    def _default_global_config(self):
        return {
            "title_height": 24,
            "title_size": 10,
            "title_offset": 2,
            "name_size": 8,
            "grid_width": 4,
            "bg_color": "#202020",
            "title_color": "#ffffff",
        }

    def _load_global(self):
        if not self.CONFIG_FILE.exists():
            defaults = self._default_global_config()
            save_global_config(defaults)
            return defaults
        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
        except Exception:
            stored = {}
        merged = self._default_global_config()
        merged.update(stored)
        return merged

    # ------------------------
    # Zone management
    # ------------------------
    def _load_saved_zones(self):
        if not ZONES_DIR.exists():
            return
        for p in ZONES_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                folder = data.get("folder") or None
                title = data.get("title", "Zone")
                z = Zone(title=title, folder=folder, defaults=self.global_config)
                for k, v in data.items():
                    if hasattr(z, k) and k != "geometry":
                        setattr(z, k, v)
                geom = data.get("geometry")
                if geom and len(geom) == 4:
                    z.setGeometry(QRect(*geom))
                else:
                    z.adjust_window_size()
                z.refresh_grid()
                self.zones.append(z)
                z.show()
            except Exception as e:
                print(f"Failed to load zone {p}: {e}")

    def add_zone(self):
        z = Zone(title="Zone", folder=None, defaults=self.global_config)
        z.adjust_window_size()
        z.refresh_grid()
        self.zones.append(z)
        z.show()
        z.auto_save()

    def global_customize(self):
        from customizer import CustomizerDialog
        dlg = CustomizerDialog(self.global_config, mode="Global")
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.show()

    # ------------------------
    # Quit
    # ------------------------
    def quit(self):
        for z in self.zones:
            z.auto_save()
        sys.exit(0)


if __name__ == "__main__":
    app = TrayApp(sys.argv)
    sys.exit(app.exec())
