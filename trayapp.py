import sys, json
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog
from PyQt6.QtGui import QIcon, QAction, QColor
from PyQt6.QtCore import QRect, Qt

from zone import Zone
import saver
from saver import ZONES_DIR, SETTINGS_DIR, DEFAULT_GLOBALS, load_global_config, save_global_config, asset_path
from customizer import CustomizerDialog

def _icon_from_disk() -> QIcon:
    p = asset_path("icon.png")
    if p.exists():
        return QIcon(str(p))
    ic = QIcon.fromTheme("applications-system")
    return ic if not ic.isNull() else QIcon()

class TrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.global_config = self._load_global()

        self.tray = QSystemTrayIcon(_icon_from_disk(), self)
        self.tray.setToolTip("Egans Floatboard Zones")

        self.menu = QMenu()
        a = QAction("Add Zone", self); a.triggered.connect(self.add_zone); self.menu.addAction(a)
        g = QAction("Global Customize", self); g.triggered.connect(self.global_customize); self.menu.addAction(g)
        q = QAction("Quit", self); q.triggered.connect(self.quit); self.menu.addAction(q)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

        self.zones = []
        self._load_saved_zones()

    # Make app attributes proxy the global_config dict
    def __getattr__(self, name):
        if "global_config" in self.__dict__ and name in self.global_config:
            return self.global_config[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("global_config", "zones", "tray", "menu") or name in self.__dict__:
            return super().__setattr__(name, value)
        if "global_config" in self.__dict__ and name in self.global_config:
            self.global_config[name] = value
        else:
            super().__setattr__(name, value)

    def _load_global(self):
        merged = {**DEFAULT_GLOBALS, **load_global_config()}
        for k in ("bg_color", "name_color", "title_bg", "title_text"):
            v = merged[k]
            if isinstance(v, str):
                merged[k] = QColor(v)
        # ensure file exists & folders initialized
        save_global_config({k: (v.name() if hasattr(v, "name") else v) for k, v in merged.items()})
        return merged

    def _save_global(self):
        save_global_config(self)

    def _on_global_change(self):
        self._save_global()
        for z in self.zones:
            for key in DEFAULT_GLOBALS.keys():
                if hasattr(z, "local_overrides") and key in getattr(z, "local_overrides", set()):
                    continue
                if hasattr(self, key):
                    setattr(z, key, getattr(self, key))
            if hasattr(z, "_apply_title_style"): z._apply_title_style()
            if hasattr(z, "grid_widget"): z.grid_widget.setStyleSheet(f"background-color: {z.bg_color.name()};")
            if hasattr(z, "adjust_window_size"): z.adjust_window_size()
            if hasattr(z, "refresh_grid"): z.refresh_grid()
            if hasattr(z, "auto_save"): z.auto_save()

    def global_customize(self):
        dlg = CustomizerDialog(self.tray, self, mode="Global", on_change=self._on_global_change)
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.show()

    def _load_saved_zones(self):
        if not ZONES_DIR.exists():
            return
        for p in ZONES_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("zone_name") or data.get("title") or "Zone"
                folder = data.get("folder") or None
                z = Zone(title=title, folder=folder, defaults=self.global_config)
                for k, v in data.items():
                    if k == "geometry":
                        continue
                    if hasattr(z, k):
                        setattr(z, k, v)
                geom = data.get("geometry")
                if isinstance(geom, (list, tuple)) and len(geom) == 4:
                    z.setGeometry(QRect(*map(int, geom)))
                else:
                    z.adjust_window_size()
                z.refresh_grid()
                self.zones.append(z)
                z.show()
            except Exception as e:
                print(f"[Tray] Failed to load {p.name}: {e}")

    def add_zone(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            for d in dlg.selectedFiles():
                z = Zone(title=Path(d).name or "Zone", folder=d, defaults=self.global_config)
                z.adjust_window_size()
                z.refresh_grid()
                z.show()
                self.zones.append(z)
                z.auto_save()

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = TrayApp(sys.argv)
    sys.exit(app.exec())
