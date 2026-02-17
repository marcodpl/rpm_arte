# carplay_main.py
import json
import math
import os
import sys
from functools import partial

from PyQt5 import (QtWidgets, QtGui, QtCore)

# Try to import your real Actions class; fallback to a dumdum big ching booby ass if it's missing.
try:
    from res.actions import Actions
except Exception:
    class Actions:
        def open_music(self, *args, **kwargs):
            print("Fallback: open_music")

        def open_maps(self, *args, **kwargs):
            print("Fallback: open_maps")

        def open_messages(self, *args, **kwargs):
            print("Fallback: open_messages")

        def open_phone(self, *args, **kwargs):
            print("Fallback: open_phone")

        def open_settings(self, *args, **kwargs):
            print("Fallback: open_settings")

        def open_browser(self, *args, **kwargs):
            print("Fallback: open_browser")


class InfoBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)  # slim top bar
        self.setStyleSheet("""
            color: #adb6f7;
        """)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # Layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 10, 0)
        layout.setSpacing(20)

        # Left: connection icon
        self.conn_icon = QtWidgets.QLabel()
        self.conn_icon.setPixmap(QtGui.QPixmap("icons/wifi.png").scaled(24, 24, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        layout.addWidget(self.conn_icon, alignment=QtCore.Qt.AlignVCenter)

        # Center: spacer (date/time aligned right)
        layout.addStretch()

        # Right: date/time
        self.time_label = QtWidgets.QLabel()
        font = QtGui.QFont("Helvetica Neue", 16 , QtGui.QFont.Bold)
        self.time_label.setFont(font)
        layout.addWidget(self.time_label, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.date_label = QtWidgets.QLabel()
        font = QtGui.QFont("Helvetica Neue", 12, QtGui.QFont.Light, italic=True)
        self.date_label.setFont(font)
        layout.addWidget(self.date_label, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Update every second
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        self.update_time()

    def update_time(self):
        now = QtCore.QDateTime.currentDateTime()
        self.time_label.setText(now.toString("hh:mm"))
        self.date_label.setText(now.toString("dddd, dd MMMM"))


def load_config(path="res/buttons.json"):
    base = os.path.dirname(os.path.abspath(__file__))
    full = path if os.path.isabs(path) else os.path.join(base, path)
    if not os.path.exists(full):
        print(f"[WARN] config file not found: {full}. Using empty config.")
        return {"buttons": []}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


class IconButton(QtWidgets.QPushButton):
    """A round icon button (fixed size) with hover/pressed effects."""
    def __init__(self, icon: QtGui.QIcon = None, size: int = 84, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(int(size * 0.6), int(size * 0.6)))
        if icon:
            self.setIcon(icon)
        self.setFlat(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.setStyleSheet(f"""
            QPushButton {{
                border-radius: {int(size/5)}px;
                background-color: rgba(255,255,255,0);
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,0.10);
            }}
            QPushButton:pressed {{
                background-color: rgba(255,255,255,0.16);
            }}
        """)


class IconGridWidget(QtWidgets.QWidget):
    def __init__(self, rows=3, cols=3, parent=None, background=None):
        super().__init__(parent)
        self._base_dir = os.path.dirname(os.path.abspath(__file__))

        # grid dimensions and background
        self.rows = int(rows)
        self.cols = int(cols)
        self.background = background
        # frameless / translucent
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._bg_label = QtWidgets.QLabel(self)
        self._bg_label.setObjectName("bgLabel")
        self._bg_label.setScaledContents(True)

        self.content = QtWidgets.QWidget(self._bg_label)
        self.content.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.content.setGeometry(self._bg_label.rect())
        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)

        self.grid_widget = QtWidgets.QWidget()
        self.grid_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(18)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.topbar_widget = InfoBar(self)

        # create empty button slots
        self.buttons = []
        for r in range(self.rows):
            for c in range(self.cols):
                wrapper = QtWidgets.QWidget()
                wrapper.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                v = QtWidgets.QVBoxLayout(wrapper)
                v.setContentsMargins(0, 0, 0, 0)
                v.setSpacing(6)

                btn = IconButton(size=84)
                lbl = QtWidgets.QLabel("Label")
                lbl.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
                lbl.setFixedHeight(22)
                lbl.setWordWrap(True)
                lbl.setStyleSheet("color: rgba(255,255,255,0.92); font-size: 12px;")

                v.addWidget(btn, alignment=QtCore.Qt.AlignHCenter)
                v.addWidget(lbl, alignment=QtCore.Qt.AlignHCenter)

                self.grid_layout.addWidget(wrapper, r, c, alignment=QtCore.Qt.AlignCenter)
                self.buttons.append((btn, lbl))

        self.content_layout.addStretch()
        self.content_layout.addWidget(self.grid_widget, alignment=QtCore.Qt.AlignCenter)
        self.content_layout.addStretch()

        self.close_btn = QtWidgets.QPushButton(self)
        self.close_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setToolTip("Close")
        icon = QtGui.QIcon.fromTheme("system-shutdown")
        if not icon.isNull():
            self.close_btn.setIcon(icon)
            self.close_btn.setIconSize(QtCore.QSize(24, 24))
        else:
            self.close_btn.setText("✕")

        self.close_btn.clicked.connect(QtWidgets.qApp.quit)
        self.close_btn.setStyleSheet("border:none; color: rgba(255,255,255,0.8); font-size:14px;")
        self.close_btn.raise_()

        self._drag_pos = None
        # apply background if provided
        self.apply_background(self.background)

        # optionally default callback to show index (safe)
        for idx, (b, l) in enumerate(self.buttons):
            b.clicked.connect(self._make_callback(idx))

    def _resolve_path(self, p):
        if not p:
            return None
        if os.path.isabs(p):
            return p
        candidate = os.path.join(self._base_dir, p)
        return candidate

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg_label.setGeometry(self.rect())
        self.content.setGeometry(self._bg_label.rect())
        self.close_btn.move(self.width() - self.close_btn.width() - 10, 10)

    def _make_callback(self, idx):
        def cb():
            print(f"Button {idx} clicked: label={self.buttons[idx][1].text()}")
        return cb

    def apply_background(self, bg):
        if not bg:
            self._bg_label.setStyleSheet("background: rgba(0,0,0,0.35);")
            return
        # try resolving path (support relative)
        resolved = self._resolve_path(bg)
        if resolved and os.path.isfile(resolved):
            pix = QtGui.QPixmap(resolved)
            self._bg_label.setPixmap(pix)
        else:
            # fallback to color string
            self._bg_label.setStyleSheet(f"background: {bg};")

    def set_button(self, index, icon_path=None, label_text=None):
        """
        Sets icon and label for a given button slot and RETURNS the QPushButton.
        Returns None if index invalid.
        """
        if index < 0 or index >= len(self.buttons):
            print(f"[WARN] set_button: index {index} out of range (0..{len(self.buttons)-1})")
            return None

        btn, lbl = self.buttons[index]

        # Resolve icon path; try absolute/relative file first, then theme icon
        if icon_path:
            resolved = self._resolve_path(icon_path)
            if resolved and os.path.isfile(resolved):
                icon = QtGui.QIcon(resolved)
                btn.setIcon(icon)
                btn.setIconSize(QtCore.QSize(70,70))
            else:
                # try icon theme name (like 'map' or 'multimedia-player')
                theme_icon = QtGui.QIcon.fromTheme(icon_path)
                if not theme_icon.isNull():
                    btn.setIcon(theme_icon)
                else:
                    print(f"[WARN] icon not found: '{icon_path}' (tried {resolved})")

        if label_text is not None:
            lbl.setText(label_text)

        return btn

    # Drag-to-move window handlers
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_pos is not None and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_pos = None
        event.accept()


def LoadGUI(config_path="res/buttons.json"):
    cfg = load_config(config_path)
    buttons = cfg.get("buttons", [])
    background = cfg.get("background", None)
    # allow optional rows/cols in config; default rows=2, compute cols automatically
    rows = int(cfg.get("rows", 2))
    cols = int(cfg.get("cols", max(1, math.ceil(len(buttons) / rows))))
    win = IconGridWidget(rows=rows, cols=cols, background=background)

    actions = Actions()

    for idx, btn_cfg in enumerate(buttons):
        icon = btn_cfg.get("icon")
        label = btn_cfg.get("label", f"Btn {idx}")
        action_name = btn_cfg.get("action") or btn_cfg.get("callback")

        btn = win.set_button(idx, icon_path=icon, label_text=label)
        if btn is None:
            print(f"[WARN] cannot configure button index {idx} (slot missing).")
            continue

        if action_name:
            if hasattr(actions, action_name):
                cb = getattr(actions, action_name)
                if callable(cb):
                    # connect directly; if you want to pass idx, use partial(cb, idx)
                    btn.clicked.connect(cb)
                    print(f"Connected {btn.text()} to {action_name}")
                else:
                    print(f"[WARN] action '{action_name}' exists but is not callable.")
            else:
                print(f"[WARN] Actions has no attribute '{action_name}'")

    return win


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = LoadGUI("res/buttons.json")
    win.resize(900, 520)
    win.show()
    sys.exit(app.exec_())
