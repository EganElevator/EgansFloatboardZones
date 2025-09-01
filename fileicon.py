import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize

from saver import asset_path  # new import

def human_size(path):
    """Return human-readable size string for a file."""
    try:
        size = os.path.getsize(path)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Load icon using Assets
        fallback = asset_path("placeholder.png")
        if os.path.exists(path):
            if os.path.isfile(path):
                icon = QIcon(path)
            else:
                icon = QIcon(str(fallback)) if fallback.exists() else QIcon()
        else:
            icon = QIcon(str(fallback)) if fallback.exists() else QIcon()

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(QSize(icon_size, icon_size)))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Display name (strip .lnk/.url extension)
        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        label_text = base if ext.lower() in [".lnk", ".url"] else name

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
