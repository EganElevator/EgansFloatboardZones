import os
import sys
import json
from pathlib import Path
import signal

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog
from PyQt6.QtGui import QIcon, QAction, QColor
from PyQt6.QtCore import QRect, QPoint, Qt

from zone import Zone
from saver import APP_FOLDER
from customizer import CustomizerDialog


try:
    from screeninfo import get_monitors
except ImportError:
    get_monitors = None

CONFIG_FILE = APP_FOLDER / "global_config.json"
ZONES_DIR = APP_FOLDER

DEFAULT_GLOBALS = {
    "rows": 5, "cols": 4, "cell_icon_size": 48, "text_size": 10,
    "title_text_size": 14, "title_height": 28, "label_height": 16,
    "scale_offset_x": 1, "scale_offset_y": 1,
    "bg_color": "#323232", "name_color": "#ffffff", "title_bg": "#9f00f0", "title_text": "#ffffff"
}


class TrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.global_config = self._load_global()
        self.tray = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray.setToolTip("Egans Floatboard Zones")
        self.menu = QMenu()

        add_zone_action = QAction("Add Zone", self)
        add_zone_action.triggered.connect(self.add_zone)
        self.menu.addAction(add_zone_action)

        global_custom = QAction("Global Customize", self)
        global_custom.triggered.connect(self.global_customize)
        self.menu.addAction(global_custom)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

        self.zones = []
        self._load_saved_zones()

    def __getattr__(self, name):
        if name in self.global_config:
            return self.global_config[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("global_config", "zones", "tray", "menu") or name in self.__dict__:
            super().__setattr__(name, value)
        elif "global_config" in self.__dict__ and name in self.global_config:
            self.global_config[name] = value
        else:
            super().__setattr__(name, value)

    def _load_global(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                merged = {**DEFAULT_GLOBALS, **cfg}
            except Exception:
                merged = DEFAULT_GLOBALS.copy()
        else:
            merged = DEFAULT_GLOBALS.copy()

        # normalize colors to QColor
        for key in ("bg_color", "name_color", "title_bg", "title_text"):
            val = merged[key]
            if isinstance(val, str):
                merged[key] = QColor(val)

        return merged


    def _save_global(self):
        APP_FOLDER.mkdir(parents=True, exist_ok=True)
        serializable = self.global_config.copy()
        for key in ("bg_color", "name_color", "title_bg", "title_text"):
            if hasattr(serializable[key], "name"):
                serializable[key] = serializable[key].name()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

    def _on_global_change(self):
        # read updated attributes from self (CustomizerDialog sets attrs directly on self)
        # build serializable global_config and save
        for key in ("rows", "cols", "cell_icon_size", "text_size", "title_text_size",
                    "title_height", "label_height", "scale_offset_x", "scale_offset_y",
                    "bg_color", "name_color", "title_bg", "title_text"):
            if hasattr(self, key):
                val = getattr(self, key)
                self.global_config[key] = val
        self._save_global()

        # Apply to zones that do NOT have local overrides for that attribute
        for z in self.zones:
            for key in ("rows", "cols", "cell_icon_size", "text_size", "title_text_size",
                        "title_height", "label_height", "scale_offset_x", "scale_offset_y",
                        "bg_color", "name_color", "title_bg", "title_text"):
                if hasattr(z, "local_overrides") and key in z.local_overrides:
                    continue
                if hasattr(self, key):
                    setattr(z, key, getattr(self, key))
            z._apply_title_style()
            z.grid_widget.setStyleSheet(f"background-color: {z.bg_color.name()};")
            z.adjust_window_size()
            z.refresh_grid()
            z.auto_save()


    def global_customize(self):
        dlg = CustomizerDialog(None, self, mode="Global", global_ref=None, on_change=self._on_global_change)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.show()


        # save updated config
        self._save_global()

        # apply new global settings to all zones that don’t have overrides
        for z in self.zones:
            z._apply_title_style()
            z.grid_widget.setStyleSheet(f"background-color: {z.bg_color.name()};")
            z.adjust_window_size()
            z.refresh_grid()


    def _load_saved_zones(self):
        # Load any saved zone json files in the folder
        if not ZONES_DIR.exists():
            return
        for p in ZONES_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                folder = data.get("folder") or None
                title = data.get("title", "Zone")
                z = Zone(title=title, folder=folder, defaults=self.global_config)
                # apply stored customizations
                for k, v in data.items():
                    if hasattr(z, k) and k != "geometry":
                        setattr(z, k, v)
                # geometry
                geom = data.get("geometry")
                if geom and len(geom) == 4:
                    z.setGeometry(QRect(*geom))
                else:
                    z.adjust_window_size()
                z.refresh_grid()
                self.zones.append(z)
                z.show()
            except Exception:
                continue

    def add_zone(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            dirs = dlg.selectedFiles()
            for d in dirs:
                z = Zone(title=os.path.basename(d) or "Zone", folder=d, defaults=self.global_config)
                z.adjust_window_size()
                z.refresh_grid()
                z.show()
                self.zones.append(z)
                z.auto_save()

    def centered_geometry(self, w, h):
        screen = self.primaryScreen().geometry()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + (screen.height() - h) // 2
        return QRect(x, y, w, h)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = TrayApp(sys.argv)
    sys.exit(app.exec())
