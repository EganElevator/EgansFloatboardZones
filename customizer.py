from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QSpinBox, QLineEdit, QCheckBox, QWidget, QHBoxLayout
)
from PyQt6.QtGui import QColor
from saver import save_zone_config, save_global_config


class CustomizerDialog(QDialog):
    def __init__(self, parent, target, mode="Local", global_ref=None, on_change=None):
        """
        parent: QWidget parent
        target: object (Zone or TrayApp) that holds config attrs
        mode: "Local" (checkboxes) or "Global" (no checkboxes)
        global_ref: reference to global config object (used to revert when override unchecked)
        on_change: optional callback to call after changes are applied (for propagation)
        """
        super().__init__(parent)
        self.setWindowTitle(f"{mode} Customizer")
        self.mode = mode
        self.target = target
        self.global_ref = global_ref
        self.on_change = on_change
        self.layout = QFormLayout(self)

        # store widgets: either widget or (widget, checkbox)
        self.widgets: dict[str, object] = {}

        # === numeric values ===
        self.add_spin("rows", "Rows:", 1, 50, getattr(target, "rows"))
        self.add_spin("cols", "Cols:", 1, 50, getattr(target, "cols"))
        self.add_spin("scale_offset_x", "Offset X:", -200, 200, getattr(target, "scale_offset_x"))
        self.add_spin("scale_offset_y", "Offset Y:", -200, 200, getattr(target, "scale_offset_y"))
        self.add_spin("text_size", "Label Font (px):", 6, 48, getattr(target, "text_size"))
        self.add_spin("title_text_size", "Title Font (px):", 8, 72, getattr(target, "title_text_size"))

        # === colors (hex) ===
        def hex_val(v):
            if hasattr(v, "name"):
                return v.name()
            return str(v)

        self.add_line("bg_color", "Background (HEX):", hex_val(getattr(target, "bg_color")))
        self.add_line("name_color", "Name Color (HEX):", hex_val(getattr(target, "name_color")))
        self.add_line("title_bg", "Title BG (HEX):", hex_val(getattr(target, "title_bg")))
        self.add_line("title_text", "Title Text (HEX):", hex_val(getattr(target, "title_text")))

        # set dialog fixed (non-resizable)
        self.setFixedSize(self.sizeHint())
        self.setSizeGripEnabled(False)

        # connect signals AFTER widgets created so lambdas capture attr correctly
        for attr, widget in self.widgets.items():
            if isinstance(widget, tuple):
                control, chk = widget
                if isinstance(control, QSpinBox):
                    control.valueChanged.connect(lambda _v, a=attr: self.live_apply(a))
                else:
                    control.textChanged.connect(lambda _t, a=attr: self.live_apply(a))
                chk.stateChanged.connect(lambda _s, a=attr: self.live_apply(a))
            else:
                w = widget
                if isinstance(w, QSpinBox):
                    w.valueChanged.connect(lambda _v, a=attr: self.live_apply(a))
                else:
                    w.textChanged.connect(lambda _t, a=attr: self.live_apply(a))

    def add_spin(self, attr, label, mn, mx, val):
        spin = QSpinBox()
        spin.setRange(mn, mx)
        spin.setValue(int(val))

        if self.mode == "Local":
            chk = QCheckBox("Override")
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(spin)
            h.addWidget(chk)
            self.layout.addRow(label, container)
            self.widgets[attr] = (spin, chk)
        else:
            self.layout.addRow(label, spin)
            self.widgets[attr] = spin

    def add_line(self, attr, label, val):
        line = QLineEdit(str(val))
        if self.mode == "Local":
            chk = QCheckBox("Override")
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(line)
            h.addWidget(chk)
            self.layout.addRow(label, container)
            self.widgets[attr] = (line, chk)
        else:
            self.layout.addRow(label, line)
            self.widgets[attr] = line

    def live_apply(self, changed_attr=None):
        """
        Apply changes immediately to target.
        For Local mode: apply only attributes with checkbox checked; if unchecked, revert from global_ref if provided.
        """
        for attr, widget in self.widgets.items():
            # Global mode (widget is direct)
            if self.mode == "Global" and not isinstance(widget, tuple):
                w = widget
                if isinstance(w, QSpinBox):
                    setattr(self.target, attr, int(w.value()))
                else:
                    text = w.text().strip()
                    c = QColor(text)
                    if c.isValid():
                        setattr(self.target, attr, c)

            # Local mode (widget is (control, checkbox))
            elif isinstance(widget, tuple):
                control, chk = widget
                if chk.isChecked():
                    # apply override and mark it
                    if not hasattr(self.target, "local_overrides"):
                        self.target.local_overrides = set()
                    self.target.local_overrides.add(attr)

                    if isinstance(control, QSpinBox):
                        setattr(self.target, attr, int(control.value()))
                    else:
                        text = control.text().strip()
                        c = QColor(text)
                        if c.isValid():
                            setattr(self.target, attr, c)
                else:
                    # remove override mark
                    if hasattr(self.target, "local_overrides") and attr in self.target.local_overrides:
                        self.target.local_overrides.discard(attr)
                    # revert to global if provided
                    if self.global_ref is not None and hasattr(self.global_ref, attr):
                        setattr(self.target, attr, getattr(self.global_ref, attr))

        # After applying values, refresh the UI on the target if possible
        if hasattr(self.target, "_apply_title_style"):
            self.target._apply_title_style()
        if hasattr(self.target, "grid_widget"):
            bg = getattr(self.target, "bg_color")
            if hasattr(bg, "name"):
                self.target.grid_widget.setStyleSheet(f"background-color: {bg.name()};")
            else:
                self.target.grid_widget.setStyleSheet(f"background-color: {str(bg)};")
        if hasattr(self.target, "adjust_window_size"):
            self.target.adjust_window_size()
        if hasattr(self.target, "refresh_grid"):
            self.target.refresh_grid()
        # Persist changes using saver.py
        try:
            if self.mode == "Global":
                save_global_config(self.target)
            else:
                save_zone_config(self.target)
        except Exception as e:
            print(f"[Customizer] Failed to save settings: {e}")


        # call external callback if provided (used by TrayApp to propagate global changes)
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass
