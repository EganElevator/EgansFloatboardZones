import os
import sys
import signal
import math
import win32gui
import win32con

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSystemTrayIcon,
    QMenu, QFileDialog, QGridLayout, QFrame, QColorDialog
)
from PyQt6.QtGui import QIcon, QAction, QCursor
from PyQt6.QtCore import Qt, QRect, QSize, QPoint

try:
    from screeninfo import get_monitors
except ImportError:
    get_monitors = None


def human_size(path):
    try:
        size = os.path.getsize(path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
    except Exception:
        return ""
    return ""


class FileIcon(QFrame):
    def __init__(self, path, icon_size=64, parent=None):
        super().__init__(parent)
        self.path = path
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(icon_size + 20, icon_size + 40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        icon = QIcon("placeholder.png")
        if os.path.exists(path):
            if os.path.isfile(path):
                icon = QIcon(path)
            else:
                icon = QIcon("placeholder.png")

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(QSize(icon_size, icon_size)))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        if ext.lower() in [".lnk", ".url"]:
            label_text = base
        else:
            label_text = name

        self.text_label = QLabel(label_text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.text_label.setWordWrap(True)
        self.text_label.setFixedHeight(32)

        tooltip = f"{name}\n{human_size(path)}"
        self.setToolTip(tooltip)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                os.startfile(self.path)
            except Exception as e:
                print("Failed to open:", self.path, e)


class Zone(QMainWindow):
    RESIZE_MARGIN = 6

    def __init__(self, title="Zone", paths=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )

        self.drag_pos = None
        self.resizing = False
        self.resize_dir = None
        self.locked = False
        self.collapsed = False

        self.title_color = "#323232"
        self.body_color = "#202020"

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Title bar
        self.title_bar = QLabel(title)
        self.title_bar.setStyleSheet(f"background-color: {self.title_color}; color: white; padding: 4px;")
        self.title_bar.setFixedHeight(24)
        self.layout.addWidget(self.title_bar)

        # Grid area
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(8)
        self.grid_widget.setStyleSheet(f"background-color: {self.body_color};")
        self.layout.addWidget(self.grid_widget)

        self.setCentralWidget(container)

        self.paths = paths or []
        self.populate()

        # Right-click menu for title bar
        self.title_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.title_bar.customContextMenuRequested.connect(self.open_title_menu)

    def populate(self):
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        cols = 4
        row, col = 0, 0
        for path in self.paths:
            icon_widget = FileIcon(path, 48)
            self.grid_layout.addWidget(icon_widget, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def open_title_menu(self, pos):
        menu = QMenu(self)
        lock_action = menu.addAction("Unlock Zone" if self.locked else "Lock Zone")
        color_action = menu.addAction("Edit Colors (HEX)")
        action = menu.exec(QCursor.pos())
        if action == lock_action:
            self.toggle_lock()
        elif action == color_action:
            self.edit_colors()

    def toggle_lock(self):
        self.locked = not self.locked
        hwnd = self.winId().__int__()
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if self.locked:
            ex_style |= win32con.WS_EX_TRANSPARENT
        else:
            ex_style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    def edit_colors(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.body_color = color.name()
            self.grid_widget.setStyleSheet(f"background-color: {self.body_color};")
        color = QColorDialog.getColor()
        if color.isValid():
            self.title_color = color.name()
            self.title_bar.setStyleSheet(f"background-color: {self.title_color}; color: white; padding: 4px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() <= self.title_bar.height():
                self.drag_pos = event.globalPosition().toPoint()
            else:
                self.start_resize(event)

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            diff = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + diff)
            self.drag_pos = event.globalPosition().toPoint()
        elif self.resizing:
            self.perform_resize(event)
        else:
            self.update_cursor(event)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        self.resizing = False
        self.resize_dir = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= self.title_bar.height():
            self.toggle_collapse()

    def toggle_collapse(self):
        if self.collapsed:
            self.grid_widget.show()
        else:
            self.grid_widget.hide()
        self.collapsed = not self.collapsed

    def update_cursor(self, event):
        pos = event.position().toPoint()
        rect = self.rect()
        margin = self.RESIZE_MARGIN
        if pos.x() < margin and pos.y() < margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            self.resize_dir = "topleft"
        elif pos.x() > rect.width() - margin and pos.y() < margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            self.resize_dir = "topright"
        elif pos.x() < margin and pos.y() > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            self.resize_dir = "bottomleft"
        elif pos.x() > rect.width() - margin and pos.y() > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            self.resize_dir = "bottomright"
        elif pos.x() < margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.resize_dir = "left"
        elif pos.x() > rect.width() - margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.resize_dir = "right"
        elif pos.y() < margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.resize_dir = "top"
        elif pos.y() > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.resize_dir = "bottom"
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.resize_dir = None

    def start_resize(self, event):
        if self.resize_dir:
            self.resizing = True
            self.drag_pos = event.globalPosition().toPoint()
            self.start_geom = self.geometry()

    def perform_resize(self, event):
        if not self.resize_dir:
            return
        diff = event.globalPosition().toPoint() - self.drag_pos
        geom = QRect(self.start_geom)
        if "left" in self.resize_dir:
            geom.setLeft(geom.left() + diff.x())
        if "right" in self.resize_dir:
            geom.setRight(geom.right() + diff.x())
        if "top" in self.resize_dir:
            geom.setTop(geom.top() + diff.y())
        if "bottom" in self.resize_dir:
            geom.setBottom(geom.bottom() + diff.y())
        self.setGeometry(geom)


class TrayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.tray = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray.setToolTip("Egans Floatboard Zones")
        self.menu = QMenu()

        add_zone_action = QAction("Add Zone", self)
        add_zone_action.triggered.connect(self.add_zone)
        self.menu.addAction(add_zone_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.show()

        self.zones = []
        self.add_zone()

    def add_zone(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            dirs = dlg.selectedFiles()
            for d in dirs:
                paths = [os.path.join(d, f) for f in os.listdir(d)]
                zone = Zone(paths=paths)
                zone.setGeometry(self.centered_geometry(500, 400))
                zone.show()
                self.zones.append(zone)

    def centered_geometry(self, w, h):
        screen = self.primaryScreen().geometry()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + (screen.height() - h) // 2
        return QRect(x, y, w, h)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = TrayApp(sys.argv)
    sys.exit(app.exec())
