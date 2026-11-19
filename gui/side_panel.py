"""Bang dieu khien ben trai (kieu GeoGebra): 3 tab  So hoc | Hinh hoc | Thong tin."""
from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QBrush, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core import builders
from core.commands import HELP_TEXT, next_point_name, run_command
from core.describe import describe, fmt, fmt_vec
from core.geometry import MeasureData, SegmentData

# ======================================================================
#  Icon ve bang code (khong can file anh)
# ======================================================================
_LINE = QColor(60, 66, 105)
_FILL = QColor(140, 180, 245, 130)
_FILL2 = QColor(245, 190, 140, 120)
_DOT = QColor(25, 55, 210)
_ORANGE = QColor(235, 120, 20)
_GREEN = QColor(20, 150, 80)
_RED = QColor(215, 40, 40)


def _pen(p: QPainter, col: QColor = _LINE, w: float = 1.6) -> None:
    p.setPen(QPen(col, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))


def _dot(p: QPainter, x: float, y: float, col: QColor = _DOT, r: float = 3.4) -> None:
    p.setPen(QPen(QColor(20, 25, 60), 1.0))
    p.setBrush(QBrush(col))
    p.drawEllipse(QPointF(x, y), r, r)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _poly(p: QPainter, pts, fill: QColor | None = None) -> None:
    _pen(p)
    p.setBrush(QBrush(fill) if fill else Qt.BrushStyle.NoBrush)
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _line(p: QPainter, a, b, col: QColor = _LINE, w: float = 1.6) -> None:
    _pen(p, col, w)
    p.drawLine(QPointF(*a), QPointF(*b))


def _dashed(p: QPainter, a, b) -> None:
    p.setPen(QPen(_LINE, 1.1, Qt.PenStyle.DashLine))
    p.drawLine(QPointF(*a), QPointF(*b))


def _ic_point(p):
    _dot(p, 22, 25, _DOT, 4.8)
    f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
    _pen(p, _LINE); p.drawText(QPointF(27, 17), "A")


def _ic_midpoint(p):
    _line(p, (7, 33), (37, 11)); _dot(p, 7, 33); _dot(p, 37, 11); _dot(p, 22, 22, _ORANGE, 4.0)


def _ic_on_segment(p):
    _line(p, (7, 33), (37, 11)); _dot(p, 7, 33); _dot(p, 37, 11)
    _dot(p, 7 + 30 * 0.3, 33 - 22 * 0.3, _GREEN, 4.0)


def _ic_divide(p):
    _line(p, (7, 33), (37, 11)); _dot(p, 7, 33); _dot(p, 37, 11)
    _dot(p, 7 + 30 * 0.66, 33 - 22 * 0.66, _ORANGE, 4.0)
    f = QFont(); f.setPointSize(7); p.setFont(f); _pen(p, _LINE)
    p.drawText(QPointF(8, 14), "m:n")


def _ic_symmetric(p):
    _dashed(p, (8, 31), (36, 13)); _dot(p, 8, 31); _dot(p, 36, 13); _dot(p, 22, 22, _ORANGE, 4.0)


def _ic_segment(p):
    _line(p, (8, 32), (36, 12), w=2.0); _dot(p, 8, 32); _dot(p, 36, 12)


def _ic_face(p):
    pts = [(8, 31), (15, 11), (33, 9), (37, 30)]
    _poly(p, pts, _FILL)
    for x, y in pts:
        _dot(p, x, y, r=3.0)


def _ic_face3(p):
    pts = [(8, 33), (22, 9), (37, 31)]
    _poly(p, pts, _FILL)
    for x, y in pts:
        _dot(p, x, y, r=3.0)


def _ic_cube(p):
    _poly(p, [(7, 18), (27, 18), (27, 38), (7, 38)], _FILL)
    _poly(p, [(7, 18), (27, 18), (37, 8), (17, 8)], _FILL2)
    _poly(p, [(27, 18), (37, 8), (37, 28), (27, 38)], _FILL2)


def _ic_box(p):
    _poly(p, [(5, 20), (30, 20), (30, 37), (5, 37)], _FILL)
    _poly(p, [(5, 20), (30, 20), (39, 11), (14, 11)], _FILL2)
    _poly(p, [(30, 20), (39, 11), (39, 28), (30, 37)], _FILL2)


def _ic_pyramid(p):
    base = [(6, 33), (30, 33), (39, 24), (15, 24)]
    apex = (22, 6)
    _poly(p, base, _FILL)
    for b in base:
        _line(p, apex, b, w=1.3)
    _dot(p, *apex, r=2.8)


def _ic_prism(p):
    bot = [(7, 35), (27, 35), (37, 28)]
    top = [(7, 12), (27, 12), (37, 5)]
    _poly(p, bot, _FILL)
    _poly(p, top, _FILL2)
    for a, b in zip(bot, top):
        _line(p, a, b, w=1.4)


def _ic_cylinder(p):
    _pen(p)
    p.setBrush(QBrush(_FILL))
    p.drawRect(QRectF(9, 11, 26, 22))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(_FILL))
    p.drawEllipse(QRectF(9, 28, 26, 10))
    p.setBrush(QBrush(_FILL2)); _pen(p)
    p.drawEllipse(QRectF(9, 6, 26, 10))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(9, 28, 26, 10), 180 * 16, 180 * 16)


def _ic_cone(p):
    _pen(p)
    p.setBrush(QBrush(_FILL))
    p.drawPolygon(QPolygonF([QPointF(22, 5), QPointF(35, 31), QPointF(9, 31)]))
    p.setBrush(QBrush(_FILL2))
    p.drawEllipse(QRectF(9, 26, 26, 10))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _ic_sphere(p):
    _pen(p)
    p.setBrush(QBrush(_FILL))
    p.drawEllipse(QRectF(7, 7, 30, 30))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(7, 17, 30, 10), 180 * 16, 180 * 16)
    p.setPen(QPen(_LINE, 1.0, Qt.PenStyle.DashLine))
    p.drawArc(QRectF(7, 17, 30, 10), 0, 180 * 16)


def _ic_distance(p):
    _line(p, (7, 31), (37, 13)); _dot(p, 7, 31); _dot(p, 37, 13)
    f = QFont(); f.setPointSize(10); f.setItalic(True); p.setFont(f)
    _pen(p, _ORANGE); p.drawText(QPointF(19, 34), "d")


def _ic_angle(p):
    _line(p, (9, 34), (37, 34)); _line(p, (9, 34), (30, 9))
    _pen(p, _ORANGE, 1.6)
    p.drawArc(QRectF(-5, 20, 28, 28), 0, 52 * 16)
    _dot(p, 9, 34, r=3.0)


def _ic_visible(p):
    _pen(p, _LINE, 1.8)
    p.drawArc(QRectF(6, 10, 32, 24), 15 * 16, 150 * 16)
    p.drawArc(QRectF(6, 10, 32, 24), 195 * 16, 150 * 16)
    p.setBrush(QBrush(_DOT)); p.drawEllipse(QPointF(22, 22), 5, 5); p.setBrush(Qt.BrushStyle.NoBrush)


def _ic_rename(p):
    f = QFont(); f.setPointSize(14); f.setBold(True); p.setFont(f)
    _pen(p, _LINE); p.drawText(QPointF(7, 29), "Aa")
    _line(p, (7, 35), (37, 35), _ORANGE, 2.0)


def _ic_color(p):
    cols = [QColor(235, 60, 60), QColor(250, 200, 40), QColor(60, 190, 90), QColor(50, 110, 235)]
    for i, c in enumerate(cols):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(c))
        p.drawPie(QRectF(7, 7, 30, 30), (90 - i * 90) * 16, -90 * 16)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _ic_delete(p):
    _line(p, (10, 10), (34, 34), _RED, 3.0); _line(p, (34, 10), (10, 34), _RED, 3.0)

def _ico_alt_plane(p: QPainter):
    # Vẽ mặt phẳng nằm dưới và đường vuông góc từ trên hạ xuống
    p.setPen(QPen(QColor(150, 160, 180), 2))
    p.drawLine(6, 34, 38, 34) # Mặt đáy
    p.setPen(QPen(QColor(220, 50, 50), 2))
    p.drawLine(22, 8, 22, 34) # Đường cao đỏ
    # Ký hiệu góc vuông nhỏ
    p.setPen(QPen(QColor(60, 60, 60), 1))
    p.drawLine(22, 28, 28, 28)
    p.drawLine(28, 28, 28, 34)

def _ico_alt_line(p: QPainter):
    # Vẽ đoạn thẳng chéo và đường vuông góc hạ xuống
    p.setPen(QPen(QColor(60, 60, 80), 2))
    p.drawLine(6, 36, 38, 20)
    p.setPen(QPen(QColor(220, 50, 50), 2))
    p.drawLine(14, 8, 22, 28)


def _ico_bisector(p: QPainter):
    # Vẽ góc và tia phân giác ở giữa
    p.setPen(QPen(QColor(60, 60, 80), 2))
    p.drawLine(8, 36, 36, 36) # Cạnh đáy
    p.drawLine(8, 36, 30, 10) # Cạnh bên
    p.setPen(QPen(QColor(240, 140, 20), 2))
    p.drawLine(8, 36, 36, 22) # Tia phân giác cam

def _ico_perp_plane(p: QPainter):
    # Đoạn thẳng xuyên qua tấm kính ở giữa
    p.setPen(QPen(QColor(70, 130, 220), 2))
    p.drawRect(14, 8, 16, 28) # Mặt phẳng trung trực
    p.setPen(QPen(QColor(220, 50, 50), 2))
    p.drawLine(4, 22, 40, 22) # Đoạn thẳng xuyên qua


_ICONS = {
    "point": _ic_point, "midpoint": _ic_midpoint, "on_segment": _ic_on_segment,
    "divide": _ic_divide, "symmetric": _ic_symmetric, "segment": _ic_segment,
    "face": _ic_face, "face3": _ic_face3, "cube": _ic_cube, "box": _ic_box,
    "pyramid": _ic_pyramid, "prism": _ic_prism, "cylinder": _ic_cylinder,
    "cone": _ic_cone, "sphere": _ic_sphere, "distance": _ic_distance, "angle": _ic_angle,
    "visible": _ic_visible, "rename": _ic_rename, "color": _ic_color, "delete": _ic_delete,
    "altitude_plane": _ico_alt_plane,
    "altitude_line": _ico_alt_line,
    "bisector": _ico_bisector,
    "perp_bisector": _ico_perp_plane,
}


def make_icon(key: str, size: int = 44) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fn = _ICONS.get(key)
    if fn:
        fn(p)
    p.end()
    return QIcon(pm)


def _swatch(color) -> QIcon:
    pm = QPixmap(12, 12)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setPen(QPen(QColor(90, 90, 100), 1))
    p.setBrush(QBrush(QColor.fromRgbF(color[0], color[1], color[2])))
    p.drawRect(1, 1, 10, 10)
    p.end()
    return QIcon(pm)


# ======================================================================
#  Widget dung chung
# ======================================================================
def _heading(text: str) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 8, 0, 2)
    v.setSpacing(2)
    lb = QLabel(text)
    f = lb.font(); f.setPointSize(f.pointSize() + 1); f.setBold(True)
    lb.setFont(f)
    v.addWidget(lb)
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet("color:#c9cdd6;")
    v.addWidget(line)
    return w


_TOOL_STYLE = """
QToolButton { border: 1px solid transparent; border-radius: 6px; padding: 3px; font-size: 9pt; }
QToolButton:hover { background: #e8eefc; border-color: #b9c8f2; }
QToolButton:pressed { background: #d3defa; }
"""


class _ToolGrid(QWidget):
    COLS = 3

    def __init__(self) -> None:
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(2)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._n = 0
        self.setStyleSheet(_TOOL_STYLE)

    def add_tool(self, key: str, text: str, cb, tip: str | None = None) -> None:
        b = QToolButton()
        b.setText(text)
        b.setIcon(make_icon(key))
        b.setIconSize(QSize(40, 40))
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        b.setFixedSize(86, 78)
        b.setAutoRaise(True)
        b.setToolTip(tip or text.replace("\n", " "))
        b.clicked.connect(lambda _checked=False, f=cb: f())
        self.grid.addWidget(b, self._n // self.COLS, self._n % self.COLS)
        self._n += 1


# ======================================================================
#  Tab 1: So hoc  (ve bang cach nhap so / lenh)
# ======================================================================
class _NumericTab(QWidget):
    def __init__(self, panel: "SidePanel") -> None:
        super().__init__()
        self.panel = panel
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 4, 8, 8)

        v.addWidget(_heading("Nhập lệnh"))
        self.cmd = QLineEdit()
        self.cmd.setPlaceholderText("Nhập lệnh…  vd: A=(1,2,3)")
        self.cmd.setClearButtonEnabled(True)
        self.cmd.returnPressed.connect(self._run)
        v.addWidget(self.cmd)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        v.addWidget(self.msg)

        self.btn_help = QToolButton()
        self.btn_help.setText("Ví dụ lệnh ▸")
        self.btn_help.setCheckable(True)
        self.btn_help.setAutoRaise(True)
        self.btn_help.toggled.connect(self._toggle_help)
        v.addWidget(self.btn_help, alignment=Qt.AlignmentFlag.AlignLeft)
        self.help = QLabel(HELP_TEXT)
        self.help.setStyleSheet(
            "background:#f4f6fb; border:1px solid #d9deea; border-radius:4px;"
            "padding:6px; font-family:Consolas,'DejaVu Sans Mono',monospace; font-size:8.5pt;"
        )
        self.help.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.help.hide()
        v.addWidget(self.help)

        v.addWidget(_heading("Thêm điểm theo tọa độ"))
        r = QHBoxLayout()
        r.addWidget(QLabel("Tên"))
        self.pt_name = QLineEdit()
        self.pt_name.setPlaceholderText("tự đặt")
        self.pt_name.setMaximumWidth(80)
        r.addWidget(self.pt_name)
        r.addStretch(1)
        v.addLayout(r)

        r = QHBoxLayout()
        self.spins: list[QDoubleSpinBox] = []
        for ax in ("X", "Y", "Z"):
            r.addWidget(QLabel(ax))
            sp = QDoubleSpinBox()
            sp.setRange(-100, 100)
            sp.setDecimals(3)
            sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sp.setMinimumWidth(52)
            r.addWidget(sp)
            self.spins.append(sp)
        v.addLayout(r)
        b = QPushButton("Thêm điểm")
        b.clicked.connect(self._add_point)
        v.addWidget(b)

        v.addWidget(_heading("Danh sách số liệu"))
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.itemSelectionChanged.connect(self._on_select)
        v.addWidget(self.list, 1)

    # ---- lenh ----
    def _toggle_help(self, on: bool) -> None:
        self.help.setVisible(on)
        self.btn_help.setText("Ví dụ lệnh ▾" if on else "Ví dụ lệnh ▸")

    def _run(self) -> None:
        text = self.cmd.text()
        try:
            note = run_command(self.panel.win.scene, text)
        except ValueError as e:
            self.msg.setStyleSheet("color:#c0392b;")
            self.msg.setText(str(e))
            return
        self.msg.setStyleSheet("color:#1e8449;")
        self.msg.setText("✓ " + note)
        self.cmd.clear()

    def _add_point(self) -> None:
        scene = self.panel.win.scene
        name = self.pt_name.text().strip() or next_point_name(scene)
        builders.gen_point(scene, name, [s.value() for s in self.spins])
        self.pt_name.clear()
        self.msg.setStyleSheet("color:#1e8449;")
        self.msg.setText(f"✓ Đã thêm điểm {name}")

    # ---- danh sach ----
    def refresh(self, selected: str | None) -> None:
        scene = self.panel.win.scene
        self.list.blockSignals(True)
        self.list.clear()
        order = {"point": 0, "segment": 1, "line": 1, "measure": 2}
        objs = sorted(
            (o for o in scene.objects.values() if o.kind in order),
            key=lambda o: order[o.kind],
        )
        for o in objs:
            text = None
            if o.kind == "point" and isinstance(o.value, np.ndarray):
                text = f"{o.name} = {fmt_vec(o.value)}"
            elif o.kind in ("segment", "line") and isinstance(o.value, SegmentData):
                text = f"{o.name} = {fmt(np.linalg.norm(o.value.b - o.value.a))}"
            elif o.kind == "measure" and isinstance(o.value, MeasureData):
                text = o.value.text
            if text is None:
                continue
            it = QListWidgetItem(_swatch(o.color), text)
            it.setData(Qt.ItemDataRole.UserRole, o.id)
            if not o.visible:
                it.setForeground(QColor(150, 150, 150))
            self.list.addItem(it)
            if o.id == selected:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    def select(self, oid: str | None) -> None:
        self.list.blockSignals(True)
        self.list.clearSelection()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == oid:
                self.list.setCurrentItem(it)
                break
        self.list.blockSignals(False)

    def _on_select(self) -> None:
        it = self.list.currentItem()
        if it is not None:
            self.panel.pick(it.data(Qt.ItemDataRole.UserRole))


# ======================================================================
#  Tab 2: Hinh hoc  (cac cum cong cu)
# ======================================================================
class _GeometryTab(QScrollArea):
    def __init__(self, panel: "SidePanel") -> None:
        super().__init__()
        w = panel.win
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(8, 0, 8, 8)

        sections = [
            ("Điểm", [
                ("point", "Điểm", w.add_point),
                ("midpoint", "Trung\nđiểm", w.add_midpoint),
                ("on_segment", "Điểm trên\ncạnh", w.add_on_segment),
                ("divide", "Chia đoạn", w.add_divide),
                ("symmetric", "Đối xứng", w.add_symmetry),
            ]),
            ("Đường thẳng", [
                ("segment", "Đoạn thẳng", w.add_segment),
                ("altitude_line", "Đường cao\nxuống đoạn", w.add_altitude_to_line),
                ("bisector", "Đường\nphân giác", w.add_angle_bisector),
            ]),
            ("Mặt phẳng", [
                ("face3", "Mặt qua\n3 điểm", w.add_face3),
                ("face", "Mặt\nđa giác", w.add_face),
                 ("altitude_plane", "Đường cao\nxuống MP", w.add_altitude_to_plane),
                ("perp_bisector", "MP trung\ntrực", w.add_perp_bisector_plane),
            ]),
            ("Hình có sẵn", [
                ("cube", "Lập phương", lambda: w.create_solid("cube")),
                ("box", "Hộp\nchữ nhật", lambda: w.create_solid("box")),
                ("pyramid", "Hình chóp", lambda: w.create_solid("pyramid")),
                ("prism", "Lăng trụ", lambda: w.create_solid("prism")),
            ]),
            ("Hình cong", [
                ("cylinder", "Hình trụ", lambda: w.create_solid("cylinder")),
                ("cone", "Hình nón", lambda: w.create_solid("cone")),
                ("sphere", "Hình cầu", lambda: w.create_solid("sphere")),
            ]),
            ("Đo đạc", [
                ("distance", "Khoảng\ncách", w.add_distance),
                ("angle", "Góc", w.add_angle),
            ]),
            ("Chỉnh sửa", [
                ("visible", "Ẩn / Hiện", w.toggle_visible),
                ("rename", "Đổi tên", w.rename_selected),
                ("color", "Màu sắc", w.change_color),
                ("delete", "Xóa", w.delete_selected),
            ]),
        ]
        for title, tools in sections:
            v.addWidget(_heading(title))
            g = _ToolGrid()
            for key, text, cb in tools:
                g.add_tool(key, text, cb)
            v.addWidget(g)
        v.addStretch(1)
        self.setWidget(body)


# ======================================================================
#  Tab Bezier: nhap diem kiem soat + tao duong cong Bezier
# ======================================================================
class _BezierTab(QWidget):
    def __init__(self, panel: "SidePanel") -> None:
        super().__init__()
        self.panel = panel
        w = panel.win
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 4, 8, 8)

        v.addWidget(_heading("Thêm điểm kiểm soát"))
        r = QHBoxLayout()
        r.addWidget(QLabel("Tên"))
        self.pt_name = QLineEdit()
        self.pt_name.setPlaceholderText("tự đặt")
        self.pt_name.setMaximumWidth(80)
        r.addWidget(self.pt_name)
        r.addStretch(1)
        v.addLayout(r)

        r = QHBoxLayout()
        self.spins: list[QDoubleSpinBox] = []
        for ax in ("X", "Y", "Z"):
            r.addWidget(QLabel(ax))
            sp = QDoubleSpinBox()
            sp.setRange(-100, 100)
            sp.setDecimals(3)
            sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sp.setMinimumWidth(52)
            r.addWidget(sp)
            self.spins.append(sp)
        v.addLayout(r)
        b = QPushButton("Thêm điểm")
        b.clicked.connect(self._add_point)
        v.addWidget(b)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        v.addWidget(self.msg)

        v.addWidget(_heading("Tạo đường cong Bezier"))
        r = QHBoxLayout()
        r.addWidget(QLabel("Điểm KS"))
        self.names = QLineEdit()
        self.names.setPlaceholderText("A B C D (>=2)")
        r.addWidget(self.names)
        v.addLayout(r)
        b = QPushButton("Tạo Bezier")
        b.clicked.connect(self._create)
        v.addWidget(b)

        v.addWidget(_heading("Mặt tham số (Parametric Surface)"))
        r = QHBoxLayout()
        r.addWidget(QLabel("Mẫu"))
        self.preset = QComboBox()
        self.preset.addItems(["Wave", "Saddle", "Paraboloid", "Ripple mountain", "Torus", "Sphere", "Custom"])
        self.preset.currentIndexChanged.connect(self._apply_preset)
        r.addWidget(self.preset)
        v.addLayout(r)

        for lbl, attr, default in (("X(u,v)", "xe", "u"),
                                   ("Y(u,v)", "ye", "v"),
                                   ("Z(u,v)", "ze", "u**2+v**2")):
            r = QHBoxLayout()
            r.addWidget(QLabel(lbl))
            le = QLineEdit(default)
            setattr(self, attr, le)
            r.addWidget(le)
            v.addLayout(r)

        r = QHBoxLayout()
        self.coeffs = []
        for name in ("a", "b", "c", "d"):
            r.addWidget(QLabel(name))
            sp = QDoubleSpinBox()
            sp.setRange(-100, 100)
            sp.setDecimals(3)
            sp.setValue(1.0)
            self.coeffs.append(sp)
            r.addWidget(sp)
        v.addLayout(r)

        r = QHBoxLayout()
        for lbl, attr, default in (("umin", "umin", -3.0), ("umax", "umax", 3.0),
                                   ("vmin", "vmin", -3.0), ("vmax", "vmax", 3.0)):
            r.addWidget(QLabel(lbl))
            sp = QDoubleSpinBox()
            sp.setRange(-100, 100)
            sp.setDecimals(2)
            sp.setValue(default)
            setattr(self, attr, sp)
            r.addWidget(sp)
        v.addLayout(r)

        r = QHBoxLayout()
        r.addWidget(QLabel("nu"))
        self.nu = QSpinBox()
        self.nu.setRange(2, 80)
        self.nu.setValue(25)
        r.addWidget(self.nu)
        r.addWidget(QLabel("nv"))
        self.nv = QSpinBox()
        self.nv.setRange(2, 80)
        self.nv.setValue(25)
        r.addWidget(self.nv)
        v.addLayout(r)

        b = QPushButton("Tạo mặt tham số")
        b.clicked.connect(self._create_surface)
        v.addWidget(b)

        self.surf_msg = QLabel("")
        self.surf_msg.setWordWrap(True)
        v.addWidget(self.surf_msg)

        v.addStretch(1)
        self._apply_preset(0)

    def _add_point(self) -> None:
        scene = self.panel.win.scene
        name = self.pt_name.text().strip() or next_point_name(scene)
        builders.gen_point(scene, name, [s.value() for s in self.spins])
        self.pt_name.clear()
        self.msg.setStyleSheet("color:#1e8449;")
        self.msg.setText(f"✓ Đã thêm điểm {name}")

    def _create(self) -> None:
        w = self.panel.win
        names = self.names.text().split()
        ids = [w._find_point(n) for n in names]
        if len(ids) < 2 or any(i is None for i in ids):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(w, "Lỗi", "Cần ít nhất 2 điểm hợp lệ.")
            return
        builders.gen_bezier(w.scene, [i for i in ids if i is not None], name="".join(names))
        w._refresh_tree()
        w.viewport.update()
        self.msg.setStyleSheet("color:#1e8449;")
        self.msg.setText("✓ Đã tạo đường cong Bezier")
        self.names.clear()

    def _apply_preset(self, idx: int) -> None:
        import math
        presets = {
            0: ("u", "v", "a*sin(b*u)*cos(b*v)",
                [1.0, 1.0, 0.0, 0.0], -3.0, 3.0, -3.0, 3.0),
            1: ("u", "v", "a*(u*u - v*v)",
                [1.0, 0.0, 0.0, 0.0], -3.0, 3.0, -3.0, 3.0),
            2: ("u", "v", "a*(u*u+v*v)",
                [1.0, 0.0, 0.0, 0.0], -3.0, 3.0, -3.0, 3.0),
            3: ("u", "v", "a*exp(-b*(u*u+v*v)) + c*sin(d*sqrt(u*u+v*v+1e-9))",
                [4.0, 0.15, 0.6, 3.0], -5.0, 5.0, -5.0, 5.0),
            4: ("(a+b*cos(v))*cos(u)", "(a+b*cos(v))*sin(u)", "b*sin(v)",
                [3.0, 1.0, 0.0, 0.0], 0.0, 2*math.pi, 0.0, 2*math.pi),
            5: ("a*sin(v)*cos(u)", "a*sin(v)*sin(u)", "a*cos(v)",
                [1.0, 0.0, 0.0, 0.0], 0.0, 2*math.pi, 0.0, math.pi),
        }
        if idx in presets:
            xe, ye, ze, coeffs, umin, umax, vmin, vmax = presets[idx]
            self.xe.setText(xe)
            self.ye.setText(ye)
            self.ze.setText(ze)
            for sp, val in zip(self.coeffs, coeffs):
                sp.setValue(val)
            self.umin.setValue(umin)
            self.umax.setValue(umax)
            self.vmin.setValue(vmin)
            self.vmax.setValue(vmax)

    def _create_surface(self) -> None:
        from core import builders
        w = self.panel.win
        coeffs = {chr(ord("a") + i): self.coeffs[i].value() for i in range(4)}
        try:
            oid = builders.gen_parametric_surface(
                w.scene, self.xe.text(), self.ye.text(), self.ze.text(),
                coeffs, self.umin.value(), self.umax.value(),
                self.vmin.value(), self.vmax.value(),
                self.nu.value(), self.nv.value(),
            )
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(w, "Lỗi", str(e))
            return
        w._refresh_tree()
        w.viewport.update()
        self.surf_msg.setStyleSheet("color:#1e8449;")
        self.surf_msg.setText("✓ Đã tạo mặt tham số")


# ======================================================================
#  Tab 3: Thong tin chi tiet
# ======================================================================
class _InfoTab(QWidget):
    FILTERS = [
        ("Tất cả", None),
        ("Điểm", ("point",)),
        ("Đường", ("segment", "line")),
        ("Mặt", ("face",)),
        ("Khối", ("solid",)),
        ("Mặt cong", ("surface",)),
        ("Số đo", ("measure",)),
    ]

    def __init__(self, panel: "SidePanel") -> None:
        super().__init__()
        self.panel = panel
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 4, 8, 8)

        v.addWidget(_heading("Chọn đối tượng"))
        self.combo = QComboBox()
        for name, _ in self.FILTERS:
            self.combo.addItem(name)
        self.combo.currentIndexChanged.connect(lambda _i: panel.refresh())
        v.addWidget(self.combo)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.setMinimumHeight(110)
        self.list.itemSelectionChanged.connect(self._on_select)
        v.addWidget(self.list, 2)

        v.addWidget(_heading("Chi tiết"))
        self.detail = QTextBrowser()
        self.detail.setOpenLinks(False)
        self.detail.setStyleSheet("QTextBrowser { background:#ffffff; border:1px solid #d9deea; }")
        v.addWidget(self.detail, 3)

    def refresh(self, selected: str | None) -> None:
        scene = self.panel.win.scene
        kinds = self.FILTERS[self.combo.currentIndex()][1]
        self.list.blockSignals(True)
        self.list.clear()
        for o in scene.objects.values():
            if kinds is not None and o.kind not in kinds:
                continue
            it = QListWidgetItem(_swatch(o.color), f"{o.name}   ({_kind_vi(o.kind)})")
            it.setData(Qt.ItemDataRole.UserRole, o.id)
            if not o.visible:
                it.setForeground(QColor(150, 150, 150))
            self.list.addItem(it)
            if o.id == selected:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        self.refresh_detail(selected)

    def select(self, oid: str | None) -> None:
        self.list.blockSignals(True)
        self.list.clearSelection()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == oid:
                self.list.setCurrentItem(it)
                break
        self.list.blockSignals(False)
        self.refresh_detail(oid)

    def refresh_detail(self, oid: str | None) -> None:
        bar = self.detail.verticalScrollBar()
        pos = bar.value()
        self.detail.setHtml(describe(self.panel.win.scene, oid))
        bar.setValue(pos)

    def _on_select(self) -> None:
        it = self.list.currentItem()
        if it is not None:
            self.panel.pick(it.data(Qt.ItemDataRole.UserRole))


def _kind_vi(kind: str) -> str:
    from core.describe import KIND_VI
    return KIND_VI.get(kind, kind)


# ======================================================================
#  Panel chinh
# ======================================================================
class SidePanel(QTabWidget):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.setDocumentMode(True)
        self.setMinimumWidth(300)
        self.tab_numeric = _NumericTab(self)
        self.tab_geometry = _GeometryTab(self)
        self.tab_bezier = _BezierTab(self)
        self.tab_info = _InfoTab(self)
        self.addTab(self.tab_numeric, "Số học")
        self.addTab(self.tab_geometry, "Hình học")
        self.addTab(self.tab_bezier, "Bezier")
        self.addTab(self.tab_info, "Thông tin")
        self.setCurrentIndex(1)     # mo san tab Hinh hoc
        f = self.tabBar().font()
        f.setBold(True)
        self.tabBar().setFont(f)

    def pick(self, oid: str) -> None:
        """Nguoi dung chon 1 muc trong danh sach cua panel -> dong bo ra cay + viewport."""
        self.win._select_tree_item(oid)

    def refresh(self) -> None:
        sel = self.win._selected_id()
        self.tab_numeric.refresh(sel)
        self.tab_info.refresh(sel)

    def set_selected(self, oid: str | None) -> None:
        self.tab_numeric.select(oid)
        self.tab_info.select(oid)

    def refresh_values(self) -> None:
        """Cap nhat so lieu khi diem dang chay (animation)."""
        sel = self.win._selected_id()
        self.tab_numeric.refresh(sel)
        self.tab_info.refresh_detail(sel)

    