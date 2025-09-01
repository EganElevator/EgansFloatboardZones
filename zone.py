import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QScrollArea, QMenu,
    QInputDialog, QLineEdit, QFileDialog, QVBoxLayout as QVBL, QFileIconProvider, QApplication
)
from PyQt6.QtGui import QIcon, QCursor, QColor, QFont
from PyQt6.QtCore import Qt, QSize, QFileInfo, QPoint

import saver
from saver import ZONES_DIR, save_zone_config, DEFAULT_GLOBALS
from customizer import CustomizerDialog

icon_provider = QFileIconProvider()

class Zone(QWidget):
    def __init__(self, title: str = "Zone", folder: str | None = None, defaults: dict | None = None):
        super().__init__(None)

        base_defaults = DEFAULT_GLOBALS.copy()
        if defaults:
            base_defaults.update(defaults)
        defaults = base_defaults

        # core config
        self.rows = defaults["rows"]
        self.cols = defaults["cols"]
        self.cell_icon_size = defaults["cell_icon_size"]
        self.text_size = defaults["text_size"]
        self.title_text_size = defaults["title_text_size"]
        self.title_height = defaults["title_height"]
        self.label_height = defaults["label_height"]
        self.cell_size = self.cell_icon_size + self.label_height
        self.scale_offset_x = defaults["scale_offset_x"]
        self.scale_offset_y = defaults["scale_offset_y"]

        # colors
        self.bg_color = QColor(defaults["bg_color"])
        self.name_color = QColor(defaults["name_color"])
        self.title_bg = QColor(defaults["title_bg"])
        self.title_text = QColor(defaults["title_text"])

        self.search_bar = None
        self.locked = False
        self.drag_pos: QPoint | None = None
        self.file_list: list[str] = []
        self.folder = None
        self.local_overrides: set[str] = set()

        if folder:
            self.folder = folder
            try:
                self.file_list = [os.path.join(folder, f) for f in os.listdir(folder)]
            except Exception:
                self.file_list = []

        # Window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Title bar
        self.title_bar = QLabel(title)
        self.title_bar.setFixedHeight(self.title_height)
        self._apply_title_style()
        self.title_bar.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.title_bar.customContextMenuRequested.connect(self.open_title_menu)
        self.layout.addWidget(self.title_bar)

        # Scrollable grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background-color: {self.bg_color.name()}; border:none;")
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.grid_layout.setContentsMargins(self.scale_offset_x, self.scale_offset_y, self.scale_offset_x, self.scale_offset_y)
        self.grid_layout.setSpacing(8)
        self.grid_widget.setStyleSheet(f"background-color: {self.bg_color.name()};")
        self.grid_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid_widget.customContextMenuRequested.connect(self.open_zone_menu)
        self.scroll_area.setWidget(self.grid_widget)
        self.layout.addWidget(self.scroll_area)

        self.adjust_window_size()

    # ---- small helpers ----
    def _apply_title_style(self):
        self.title_bar.setStyleSheet(
            f"background-color: {self.title_bg.name()}; "
            f"color: {self.title_text.name()}; "
            f"font-size: {self.title_text_size}px; font-weight: bold; padding-left:2px;"
        )

    def _extension_icon(self, path: str) -> QIcon:
        ext = os.path.splitext(path)[1]
        if ext == "":
            return icon_provider.icon(QFileInfo(path))
        return icon_provider.icon(QFileInfo("dummy" + ext))

    # ---------------- Dragging ----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.locked:
            local_pos = self.mapFromGlobal(event.globalPosition().toPoint())
            if self.title_bar.geometry().contains(local_pos):
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    # ---------------- Titlebar menu ----------------
    def open_title_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Change Folder", self.change_folder)
        menu.addAction("Rename Zone", self.rename_zone)
        lock_action = menu.addAction("Lock Movement")
        lock_action.setCheckable(True)
        lock_action.setChecked(self.locked)
        lock_action.triggered.connect(lambda checked: setattr(self, "locked", checked))
        menu.addAction("Customize Zone", self.customize_zone_dialog)
        menu.exec(QCursor.pos())

    # ---------------- Zone background menu - search toggle ----------------
    def open_zone_menu(self, pos):
        if self.search_bar:
            self.search_bar.deleteLater()
            self.search_bar = None
            self.refresh_grid()
        else:
            self.search_bar = QLineEdit(self.grid_widget)
            self.search_bar.setPlaceholderText("Search...")
            self.grid_layout.addWidget(self.search_bar, 0, 0, 1, self.cols)
            self.search_bar.textChanged.connect(self.apply_search)
            self.search_bar.setFocus()

    def apply_search(self, text: str):
        text = (text or "").strip().lower()
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            w = item.widget()
            if not w or w is self.search_bar:
                continue
            label = w.findChild(QLabel)
            if label:
                lbl_text = label.text().lower()
                w.setVisible(text == "" or text in lbl_text)

    # ---------------- Rename / Change folder ----------------
    def rename_zone(self):
        val, ok = QInputDialog.getText(self, "Rename Zone", "Enter new name:", text=self.title_bar.text())
        if ok and val:
            self.title_bar.setText(val)
            self.auto_save()

    def change_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder = folder
            try:
                self.file_list = [os.path.join(folder, f) for f in os.listdir(folder)]
            except Exception:
                self.file_list = []
            self.adjust_window_size()
            self.refresh_grid()
            self.auto_save()

    # ---------------- Customize dialog (LIVE) ----------------
    def customize_zone_dialog(self):
        app = QApplication.instance()
        dlg = CustomizerDialog(self, self, mode="Local", global_ref=app, on_change=getattr(app, "_on_global_change", None))
        dlg.setWindowModality(Qt.WindowModality.NonModal)
        dlg.show()

    # ---------------- Add / Refresh grid ----------------
    def add_files(self, files):
        for f in files:
            if isinstance(f, str):
                self.file_list.append(f)
            elif isinstance(f, (tuple, list)) and len(f) == 2:
                self.file_list.append(f[0])
        self.adjust_window_size()
        self.refresh_grid()
        self.auto_save()

    def refresh_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        max_chars = max(6, (self.cell_size // 7))
        start_row = 1 if self.search_bar else 0

        for idx, path in enumerate(self.file_list):
            name = os.path.basename(path)
            if name.lower().endswith((".lnk", ".url")):
                name = os.path.splitext(name)[0]
            display = name if len(name) <= max_chars else (name[: max_chars - 3] + "...")

            if os.path.isdir(path):
                icon = QIcon("Folder.png") if os.path.exists("Folder.png") else icon_provider.icon(QFileInfo(path))
            else:
                icon = self._extension_icon(path)

            btn = QPushButton()
            btn.setIcon(icon)
            btn.setIconSize(QSize(self.cell_icon_size, self.cell_icon_size))
            btn.setFixedSize(self.cell_icon_size, self.cell_icon_size)
            btn.setToolTip(name)
            btn.setStyleSheet("border:none; background:transparent;")
            btn.mouseDoubleClickEvent = lambda e, p=path: (os.startfile(p) if os.path.exists(p) else None)

            label = QLabel(display)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont(); font.setPixelSize(self.text_size)
            label.setFont(font)
            label.setStyleSheet(f"color: {self.name_color.name()};")
            label.setFixedHeight(self.label_height)
            label.setFixedWidth(self.cell_size)

            cell = QWidget()
            v = QVBL(cell); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
            v.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            cell.setFixedSize(self.cell_size, self.cell_size)
            v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            v.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

            row = idx // self.cols
            col = idx % self.cols
            self.grid_layout.addWidget(cell, row + start_row, col)

    # ---------------- Window sizing ----------------
    def adjust_window_size(self):
        v_w = self.scroll_area.verticalScrollBar().sizeHint().width()
        h_h = self.scroll_area.horizontalScrollBar().sizeHint().height()
        width = self.cols * self.cell_size + (self.scale_offset_x * 2) + (v_w * 2)
        height = self.rows * self.cell_size + self.title_bar.height() + (self.scale_offset_y * 2)
        if len(self.file_list) > self.rows * self.cols:
            height += h_h
        width = max(width, 160)
        height = max(height, self.title_bar.height() + 50)
        self.resize(width, height)

    # ---------------- Persistence ----------------
    def to_dict(self) -> dict:
        geom = self.geometry()
        return {
            "zone_name": self.title_bar.text(),
            "folder": self.folder or "",
            "rows": self.rows,
            "cols": self.cols,
            "cell_icon_size": self.cell_icon_size,
            "text_size": self.text_size,
            "title_text_size": self.title_text_size,
            "title_height": self.title_height,
            "label_height": self.label_height,
            "scale_offset_x": self.scale_offset_x,
            "scale_offset_y": self.scale_offset_y,
            "bg_color": self.bg_color.name(),
            "name_color": self.name_color.name(),
            "title_bg": self.title_bg.name(),
            "title_text": self.title_text.name(),
            "geometry": [geom.x(), geom.y(), geom.width(), geom.height()],
        }

    def auto_save(self):
        save_zone_config(self)
