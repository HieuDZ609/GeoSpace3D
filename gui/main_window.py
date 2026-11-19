"""Cua so chinh: toolbar, cay layer, panel thuoc tinh, undo/redo, che do hien thi, animation."""
from __future__ import annotations

import math
import os
import random

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.builders import (
    gen_angle,
    gen_bezier,
    gen_box,
    gen_cone,
    gen_cube,
    gen_cylinder,
    gen_distance,
    gen_divide,
    gen_face,
    gen_midpoint,
    gen_on_segment,
    gen_point,
    gen_prism,
    gen_pyramid,
    gen_segment,
    gen_sphere,
    gen_symmetric,
    gen_altitude_to_plane,
    gen_altitude_to_line,
    gen_angle_bisector,
    gen_plane_through_points,
    gen_perp_bisector_segment,
)
from core.scene import Scene
from gui.dialogs import AddPointDialog, CreateSolidDialog
from gui.side_panel import SidePanel
from gui.viewport import Viewport

GROUPS = ["Điểm", "Đoạn thẳng", "Mặt", "Khối", "Mặt cong", "Đường cong", "Số đo", "Khác"]
GROUP_MAP = {
    "Points": "Điểm",
    "Segments": "Đoạn thẳng",
    "Faces": "Mặt",
    "Solids": "Khối",
    "Surfaces": "Mặt cong",
    "Curves": "Đường cong",
    "Measures": "Số đo",
    "Other": "Khác",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GeoSpace 3D")
        self.resize(1440, 860)
        self.scene = Scene()
        self.scene.on_change(self._on_scene_changed)
        self.current_file: str | None = None
        self._refreshing: bool = False
        self._rotate_on: bool = False
        self._anim_on: bool = False

        self.viewport = Viewport()
        self.viewport.set_scene(self.scene)
        self.viewport.objectClicked.connect(self._on_viewport_click)
        self.viewport.viewStateChanged.connect(self._sync_view_actions)
        self.setCentralWidget(self.viewport)
        self.viewport.setFocus()

        self._build_toolbar()
        self._build_docks()
        self._build_anim()
        self._refresh_tree()
        self.statusBar().showMessage(
            "Chuột trái: xoay / chọn điểm, đoạn, mặt | Lăn chuột: zoom | M: đổi chế độ | "
            "L: khóa gốc O | 5: chiếu song song | Home: reset"
        )
        self.load_sample()

    # ---------------- toolbar ----------------
    def _build_toolbar(self) -> None:
        """Thanh cong cu gon: file, undo/redo, che do xem. Cong cu ve nam o panel ben trai."""
        tb = QToolBar("Công cụ")
        tb.setMovable(False)
        self.addToolBar(tb)

        def act(name: str, cb, sc: str | None = None, tip: str | None = None) -> QAction:
            a = QAction(name, self)
            if sc:
                a.setShortcut(sc)
            if tip:
                a.setToolTip(tip)
            a.triggered.connect(cb)
            tb.addAction(a)
            return a

        def toggle(name: str, checked: bool, cb, tip: str | None = None) -> QAction:
            a = QAction(name, self)
            a.setCheckable(True)
            a.setChecked(checked)
            if tip:
                a.setToolTip(tip)
            a.triggered.connect(cb)
            tb.addAction(a)
            return a

        act("Mới", self.new_project, "Ctrl+N")
        act("Mở", self.open_project, "Ctrl+O")
        act("Lưu", self.save_project, "Ctrl+S")
        act("Xuất ảnh", self.export_png)
        tb.addSeparator()
        act("Hoàn tác", self.do_undo, "Ctrl+Z")
        act("Làm lại", self.do_redo, "Ctrl+Y")
        tb.addSeparator()

        self.act_mode = act("Mặt + Khung", lambda: self.viewport.cycle_display_mode(),
                            tip="Đổi chế độ hiển thị (phím M)")
        self.act_lock_origin = toggle("Khóa gốc O", True, lambda c: self.viewport.set_lock_origin(c),
                                      "Giữ gốc O ở tâm khung nhìn (phím L)")
        self.act_ortho = toggle("Song song", False, lambda c: self.viewport.set_ortho(c),
                                "Phép chiếu song song (phím 5)")
        self.act_plane = toggle("Mặt nền", True, lambda c: self.viewport.set_show_plane(c),
                                "Hiện / ẩn mặt phẳng Oxy")
        self.act_grid = toggle("Lưới", False, lambda c: self.viewport.set_show_grid(c),
                               "Hiện / ẩn lưới ô vuông")

        
        tb.addSeparator()
        self.act_rotate = toggle("Tự xoay", False, lambda _c: self.toggle_rotate())
        self.act_anim = toggle("Chạy điểm", False, lambda _c: self.toggle_anim())

        
        # Phim tat Delete: xoa doi tuong dang chon
        a = QAction(self)
        a.setShortcut("Delete")
        a.triggered.connect(self.delete_selected)
        self.addAction(a)

    def _sync_view_actions(self) -> None:
        self.act_lock_origin.setChecked(self.viewport.lock_origin)
        self.act_ortho.setChecked(self.viewport.ortho)
        self.act_plane.setChecked(self.viewport.show_plane)
        self.act_grid.setChecked(self.viewport.show_grid)
        labels = {
            "solid": "Mặt + Khung",
            "wireframe": "Khung dây",
            "face": "Chỉ mặt",
        }
        self.act_mode.setText("Chế độ: " + labels[self.viewport.display_mode])

    # ---------------- docks ----------------
    def _build_docks(self) -> None:
        # Panel ben trai: So hoc | Hinh hoc | Thong tin
        self.panel = SidePanel(self)
        dl = QDockWidget("Công cụ", self)
        dl.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dl.setTitleBarWidget(QWidget())          # an thanh tieu de, nhin nhu panel co dinh
        dl.setMinimumWidth(310)
        dl.setWidget(self.panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dl)

        dw = QDockWidget("Quản lý đối tượng", self)
        dw.setMinimumWidth(250)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.tree.itemSelectionChanged.connect(self._on_tree_select)
        self.tree.itemChanged.connect(self._on_item_changed)
        dw.setWidget(self.tree)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dw)

        dw2 = QDockWidget("Thuộc tính", self)
        w = QWidget()
        v = QVBoxLayout(w)
        self.prop_name = QLabel("-")
        self.prop_name.setWordWrap(True)
        v.addWidget(self.prop_name)

        row = QHBoxLayout()
        self.btn_color = QPushButton("Màu sắc")
        self.btn_color.clicked.connect(self.change_color)
        row.addWidget(self.btn_color)
        self.btn_vis = QPushButton("Ẩn")
        self.btn_vis.clicked.connect(self.toggle_visible)
        row.addWidget(self.btn_vis)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Độ trong suốt"))
        self.sl_alpha = QSlider(Qt.Orientation.Horizontal)
        self.sl_alpha.setRange(0, 100)
        self.sl_alpha.setValue(40)
        self.sl_alpha.valueChanged.connect(self._alpha_changed)
        row.addWidget(self.sl_alpha)
        v.addLayout(row)

        self.coord_box = QWidget()
        cv = QVBoxLayout(self.coord_box)
        self.spins: list[QDoubleSpinBox] = []
        for axis in ("X", "Y", "Z"):
            r = QHBoxLayout()
            r.addWidget(QLabel(axis))
            sp = QDoubleSpinBox()
            sp.setRange(-1000, 1000)
            sp.setDecimals(3)
            sp.valueChanged.connect(self._coord_changed)
            r.addWidget(sp)
            self.spins.append(sp)
            cv.addLayout(r)
        v.addWidget(self.coord_box)
        self.coord_box.hide()

        self.t_box = QWidget()
        tv = QVBoxLayout(self.t_box)
        tv.addWidget(QLabel("t (điểm chạy trên cạnh)"))
        self.sl_t = QSlider(Qt.Orientation.Horizontal)
        self.sl_t.setRange(0, 1000)
        self.sl_t.setValue(500)
        self.sl_t.valueChanged.connect(self._t_changed)
        tv.addWidget(self.sl_t)
        v.addWidget(self.t_box)
        self.t_box.hide()

        v.addStretch(1)
        dw2.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dw2)

    def _build_anim(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self._phase = 0.0

    # ---------------- selection / refresh ----------------
    def _selected_id(self) -> str | None:
        it = self.tree.currentItem()
        if it is None:
            return None
        return it.data(0, Qt.ItemDataRole.UserRole)

    def _on_scene_changed(self, ids: list[str]) -> None:
        self._refresh_tree()
        self.viewport.update()
        sel = self._selected_id()
        if sel and sel in self.scene.objects:
            self._load_props(sel)

    def _refresh_tree(self) -> None:
        prev = self._selected_id()
        self._refreshing = True
        self.tree.blockSignals(True)
        self.tree.clear()

        groups: dict[str, QTreeWidgetItem] = {}
        for g in GROUPS:
            item = QTreeWidgetItem([g, ""])
            item.setExpanded(True)
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
            self.tree.addTopLevelItem(item)
            groups[g] = item

        for o in self.scene.objects.values():
            g = GROUP_MAP.get(o.group, "Khác")
            it = QTreeWidgetItem([o.name, o.kind])
            it.setData(0, Qt.ItemDataRole.UserRole, o.id)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(
                0, Qt.CheckState.Checked if o.visible else Qt.CheckState.Unchecked
            )
            it.setForeground(0, QColor.fromRgbF(*o.color[:3]))
            groups[g].addChild(it)

        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._refreshing = False
        if prev and prev in self.scene.objects:
            self._select_tree_item(prev)
        panel = getattr(self, "panel", None)
        if panel is not None:
            panel.refresh()

    def _on_tree_select(self) -> None:
        oid = self._selected_id()
        self.viewport.selected_id = oid
        self.viewport.update()
        if oid:
            self._load_props(oid)
        panel = getattr(self, "panel", None)
        if panel is not None:
            panel.set_selected(oid)

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if self._refreshing or col != 0:
            return
        oid = item.data(0, Qt.ItemDataRole.UserRole)
        if not oid or oid not in self.scene.objects:
            return
        vis = item.checkState(0) == Qt.CheckState.Checked
        o = self.scene.objects[oid]
        if o.visible != vis:
            self.scene._push()
            o.visible = vis
            self.scene.evaluate()
            self.viewport.update()
            self.statusBar().showMessage(
                f"{'Hiện' if vis else 'Ẩn'}: {o.name}", 2000
            )

    def _load_props(self, oid: str) -> None:
        o = self.scene.objects.get(oid)
        if not o:
            return
        self.prop_name.setText(f"<b>{o.name}</b> &nbsp;({o.kind})&nbsp; [{o.id}]")
        self.btn_vis.setText("Ẩn" if o.visible else "Hiện")

        self.sl_alpha.blockSignals(True)
        self.sl_alpha.setValue(int(round(o.color[3] * 100)))
        self.sl_alpha.blockSignals(False)

        if o.kind == "point" and o.ctor == "fixed" and isinstance(o.value, np.ndarray):
            self.coord_box.show()
            for i in range(3):
                self.spins[i].blockSignals(True)
                self.spins[i].setValue(float(o.value[i]))
                self.spins[i].blockSignals(False)
        else:
            self.coord_box.hide()

        if o.kind == "point" and o.ctor == "on_segment":
            self.t_box.show()
            self.sl_t.blockSignals(True)
            self.sl_t.setValue(int(float(o.params.get("t", 0.5)) * 1000))
            self.sl_t.blockSignals(False)
        else:
            self.t_box.hide()

    def _coord_changed(self) -> None:
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects.get(oid)
        if not o or o.kind != "point" or o.ctor != "fixed":
            return
        xyz = [self.spins[i].value() for i in range(3)]
        self.scene.update(oid, params={"xyz": xyz})

    def _t_changed(self) -> None:
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects.get(oid)
        if not o or o.ctor != "on_segment":
            return
        o.params["t"] = self.sl_t.value() / 1000.0
        self.scene._notify([oid])

    def _alpha_changed(self, val: int) -> None:
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        r, g, b, _ = o.color
        self.scene.update(oid, history=False, color=(r, g, b, val / 100.0))

    def toggle_visible(self) -> None:
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        self.scene.update(oid, visible=not o.visible)

    def change_color(self) -> None:
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        c = QColorDialog.getColor(QColor.fromRgbF(*o.color[:3]))
        if c.isValid():
            self.scene.update(
                oid, color=(c.redF(), c.greenF(), c.blueF(), o.color[3])
            )

    def _on_viewport_click(self, oid: str) -> None:
        if oid:
            self._select_tree_item(oid)

    def _select_tree_item(self, oid: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                ch = parent.child(j)
                if ch.data(0, Qt.ItemDataRole.UserRole) == oid:
                    self.tree.setCurrentItem(ch)
                    return

    # ---------------- context menu ----------------
    def _tree_menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        if it is None:
            return
        oid = it.data(0, Qt.ItemDataRole.UserRole)
        if not oid:
            return
        self.tree.setCurrentItem(it)
        m = QMenu(self)
        m.addAction("Đổi tên", lambda: self.rename_object(oid))
        m.addAction("Màu sắc", self.change_color)
        m.addAction("Ẩn / Hiện", self.toggle_visible)
        m.addSeparator()
        m.addAction("Xóa", self.delete_selected)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def rename_object(self, oid: str) -> None:
        o = self.scene.objects[oid]
        name, ok = QInputDialog.getText(self, "Đổi tên", "Tên mới:", text=o.name)
        if ok and name.strip():
            self.scene.update(oid, name=name.strip())

    # ---------------- actions ----------------
    def add_point(self) -> None:
        dlg = AddPointDialog(self)
        if dlg.exec():
            name, xyz = dlg.get()
            gen_point(self.scene, name, xyz)

    def add_midpoint(self) -> None:
        ids = self._ask_points(2, "Chọn 2 điểm để lấy trung điểm")
        if not ids:
            return
        raw = self._input_text(
            "Tên trung điểm", "Đặt tên (để trống = tự đặt):"
        )
        if raw is None:                     # Cancel -> thoát im lặng
            return
        name = raw.strip() or None
        gen_midpoint(self.scene, ids[0], ids[1], name=name)

    def add_on_segment(self) -> None:
        ids = self._ask_points(2, "Chọn 2 điểm (điểm chạy trên đoạn)")
        if not ids:
            return
        t = random.uniform(0.15, 0.85)
        gen_on_segment(self.scene, ids[0], ids[1], t=t)

    def add_divide(self) -> None:
        ids = self._ask_points(2, "Chọn A, B để chia đoạn")
        if not ids:
            return
        m, ok = QInputDialog.getInt(self, "Tỉ lệ", "AM:MB = m:n, nhập m:", 1, 1, 100)
        if not ok:
            return
        n, ok = QInputDialog.getInt(self, "Tỉ lệ", "Nhập n:", 1, 1, 100)
        if not ok:
            return
        gen_divide(self.scene, ids[0], ids[1], m, n)

    def add_symmetry(self) -> None:
        ids = self._ask_points(2, "Chọn điểm A và tâm đối xứng O")
        if ids:
            gen_symmetric(self.scene, ids[0], ids[1])

    def add_segment(self) -> None:
        ids = self._ask_points(2, "Chọn 2 điểm để vẽ đoạn thẳng")
        if ids:
            gen_segment(self.scene, ids[0], ids[1])

    def add_face(self) -> None:
        raw = self._input_text(
            "Mặt phẳng", "Nhập tên các điểm cách nhau bởi dấu cách (>=3):"
        )
        if raw is None:                     # Cancel -> thoát im lặng
            return
        names = raw.split()
        ids = [self._find_point(n) for n in names]
        if len(ids) < 3 or any(i is None for i in ids):
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy đủ 3 điểm hợp lệ.")
            return
        gen_face(self.scene, [i for i in ids if i is not None], name="".join(names))

    def add_bezier(self) -> None:
        raw = self._input_text(
            "Đường cong Bezier",
            "Nhập tên các điểm kiểm soát cách nhau bởi dấu cách (>=2):",
        )
        if raw is None:                     # Cancel -> thoát im lặng
            return
        names = raw.split()
        ids = [self._find_point(n) for n in names]
        if len(ids) < 2 or any(i is None for i in ids):
            QMessageBox.warning(self, "Lỗi", "Cần ít nhất 2 điểm hợp lệ.")
            return
        gen_bezier(self.scene, [i for i in ids if i is not None], name="".join(names))
        self._refresh_tree()
        self.viewport.update()

    def add_line_parametric(self, x0, y0, z0, a, b, c, L=10.0) -> None:
        import math
        if a == 0 and b == 0 and c == 0:
            QMessageBox.warning(self, "Lỗi", "Vectơ chỉ phương không thể là vectơ không.")
            return
        nrm = math.sqrt(a*a + b*b + c*c)
        dx, dy, dz = a/nrm, b/nrm, c/nrm
        p1 = (x0 - L*dx, y0 - L*dy, z0 - L*dz)
        p2 = (x0 + L*dx, y0 + L*dy, z0 + L*dz)
        from core import builders
        i1 = builders.gen_point(self.scene, "P1", p1)
        i2 = builders.gen_point(self.scene, "P2", p2)
        builders.gen_segment(self.scene, i1, i2)
        self._refresh_tree()
        self.viewport.update()

    def add_line_general_2d(self, a, b, c, L=10.0) -> None:
        import math
        if a == 0 and b == 0:
            QMessageBox.warning(self, "Lỗi", "a, b không đồng thời bằng 0.")
            return
        if abs(a) >= abs(b):
            x0, y0 = -c/a, 0.0
        else:
            x0, y0 = 0.0, -c/b
        dx, dy = -b, a
        nrm = math.sqrt(dx*dx + dy*dy)
        dx, dy = dx/nrm, dy/nrm
        p1 = (x0 - L*dx, y0 - L*dy, 0.0)
        p2 = (x0 + L*dx, y0 + L*dy, 0.0)
        from core import builders
        i1 = builders.gen_point(self.scene, "P1", p1)
        i2 = builders.gen_point(self.scene, "P2", p2)
        builders.gen_segment(self.scene, i1, i2)
        self._refresh_tree()
        self.viewport.update()

    def add_plane_equation(self, a, b, c, d, size=6.0) -> None:
        import math
        import numpy as np
        if a == 0 and b == 0 and c == 0:
            QMessageBox.warning(self, "Lỗi", "Vectơ pháp tuyến không thể là vectơ không.")
            return
        nrm = math.sqrt(a*a + b*b + c*c)
        nx, ny, nz = a/nrm, b/nrm, c/nrm
        if abs(c) > 1e-9:
            px, py, pz = 0.0, 0.0, -d/c
        elif abs(b) > 1e-9:
            px, py, pz = 0.0, -d/b, 0.0
        else:
            px, py, pz = -d/a, 0.0, 0.0
        nvec = np.array([nx, ny, nz])
        ref = np.array([0.0, 0.0, 1.0]) if abs(nz) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(nvec, ref)
        u /= np.linalg.norm(u)
        v = np.cross(nvec, u)
        v /= np.linalg.norm(v)
        corners = []
        for su in (-1, 1):
            for sv in (-1, 1):
                pt = np.array([px, py, pz]) + size*su*u + size*sv*v
                corners.append(tuple(float(x) for x in pt))
        from core import builders
        ids = [builders.gen_point(self.scene, f"Q{i}", pt) for i, pt in enumerate(corners)]
        builders.gen_face(self.scene, ids, color=(0.5, 0.7, 0.9, 0.35))
        self._refresh_tree()
        self.viewport.update()

    def add_face3(self) -> None:
        ids = self._ask_points(3, "Chọn 3 điểm để tạo mặt phẳng")
        if ids:
            gen_face(self.scene, ids)

    def rename_selected(self) -> None:
        oid = self._selected_id()
        if oid:
            self.rename_object(oid)
        else:
            self.statusBar().showMessage("Hãy chọn một đối tượng trước", 3000)

    def add_distance(self) -> None:
        ids = self._ask_points(2, "Chọn 2 điểm để đo khoảng cách")
        if ids:
            gen_distance(self.scene, ids[0], ids[1])

    def add_angle(self) -> None:
        ids = self._ask_points(3, "Chọn A, đỉnh B, C để đo góc ∠ABC")
        if ids:
            gen_angle(self.scene, ids[0], ids[1], ids[2])

    def create_solid(self, kind: str) -> None:
        dlg = CreateSolidDialog(self, kind)
        if not dlg.exec():
            return
        p = dlg.get()
        if kind == "cube":
            gen_cube(self.scene, p["A"], p["edge"])
        elif kind == "box":
            gen_box(self.scene, p["A"], p["dx"], p["dy"], p["dz"])
        elif kind == "pyramid":
            gen_pyramid(self.scene, p["side"], p["height"], center=p["A"])
        elif kind == "prism":
            gen_prism(self.scene, p["side"], p["height"], center=p["A"])
        elif kind == "cylinder":
            gen_cylinder(self.scene, p["A"], p["side"], p["height"])
        elif kind == "cone":
            gen_cone(self.scene, p["A"], p["side"], p["height"])
        elif kind == "sphere":
            gen_sphere(self.scene, p["A"], p["side"])

    def delete_selected(self) -> None:
        oid = self._selected_id()
        if not oid:
            return
        removed = self.scene.remove(oid)
        if len(removed) > 1:
            QMessageBox.information(
                self, "Xóa", f"Đã xóa {len(removed)} đối tượng (kèm phụ thuộc)."
            )

    # ---------------- animation ----------------
    def toggle_rotate(self) -> None:
        self._rotate_on = self.act_rotate.isChecked()
        self._sync_timer()

    def toggle_anim(self) -> None:
        self._anim_on = self.act_anim.isChecked()
        self._sync_timer()

    def _sync_timer(self) -> None:
        if self._rotate_on or self._anim_on:
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        self._phase += 0.06
        if self._rotate_on:
            self.viewport.yaw = (self.viewport.yaw - 0.6) % 360.0
        if self._anim_on:
            for o in self.scene.objects.values():
                if o.ctor == "on_segment":
                    o.params["t"] = 0.5 + 0.5 * math.sin(self._phase)
            self.scene.evaluate()
            self._tick_n = getattr(self, "_tick_n", 0) + 1
            if self._tick_n % 8 == 0:
                self.panel.refresh_values()
        self.viewport.update()

    # ---------------- file ----------------
    def new_project(self) -> None:
        self.scene = Scene()
        self.scene.on_change(self._on_scene_changed)
        self.viewport.set_scene(self.scene)
        self.current_file = None
        self.setWindowTitle("GeoSpace 3D")
        self._refresh_tree()
        self.viewport.update()

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Mở", "", "JSON (*.json)")
        if not path:
            return
        self.scene = Scene.load(path)
        self.scene.on_change(self._on_scene_changed)
        self.viewport.set_scene(self.scene)
        self.current_file = path
        self.setWindowTitle(f"GeoSpace 3D - {os.path.basename(path)}")
        self._refresh_tree()
        self.viewport.update()

    def save_project(self) -> None:
        if not self.current_file:
            path, _ = QFileDialog.getSaveFileName(self, "Lưu", "bai1.json", "JSON (*.json)")
            if not path:
                return
            self.current_file = path
        self.scene.save(self.current_file)
        self.statusBar().showMessage(f"Đã lưu: {self.current_file}", 4000)
        self.setWindowTitle(f"GeoSpace 3D - {os.path.basename(self.current_file)}")

    def export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Xuất PNG", "hinh.png", "PNG (*.png)")
        if not path:
            return
        self.viewport.repaint()
        img = self.viewport.grabFramebuffer()
        img.save(path)
        self.statusBar().showMessage(f"Đã xuất: {path}", 4000)

    def do_undo(self) -> None:
        if not self.scene.undo():
            self.statusBar().showMessage("Không còn gì để undo", 2000)

    def do_redo(self) -> None:
        if not self.scene.redo():
            self.statusBar().showMessage("Không còn gì để redo", 2000)

    # ---------------- sample ----------------
    def load_sample(self) -> None:
        self.new_project()
        pts = gen_pyramid(self.scene, 4.0, 5.0)["points"]
        A, B, C, D, S = pts
        M = gen_midpoint(self.scene, S, A, name="M")
        N = gen_midpoint(self.scene, S, C, name="N")
        gen_segment(self.scene, M, N, color=(0.9, 0.45, 0.0, 1.0))
        gen_distance(self.scene, M, N)
        self.statusBar().showMessage(
            "Mẫu: chóp S.ABCD + M, N là trung điểm SA, SC + đoạn MN", 6000
        )

    # ---------------- helpers ----------------
    def _input_text(self, title: str, label: str, text: str = "") -> str | None:
        """Hội thoại nhập chuỗi; trả None nếu người dùng bấm Cancel."""
        val, ok = QInputDialog.getText(self, title, label, text=text)
        return val if ok else None

    def _ask_points(self, n: int, title: str) -> list[str] | None:
        raw = self._input_text(
            title, f"Nhập tên {n} điểm cách nhau bởi dấu cách:"
        )
        if raw is None:                     # Cancel -> thoát im lặng
            return None
        names = raw.split()
        ids = [self._find_point(x) for x in names]
        if len(ids) != n or any(i is None for i in ids):
            QMessageBox.warning(self, "Lỗi", f"Cần đúng {n} điểm hợp lệ.")
            return None
        return [i for i in ids if i is not None]

    def _find_point(self, name: str) -> str | None:
        for o in self.scene.objects.values():
            if o.kind == "point" and o.name == name:
                return o.id
        return None

    def add_altitude_to_plane(self) -> None:
        """Hạ đường cao SH xuống mặt phẳng qua các điểm (ví dụ MNAB)"""
        p_name = self._input_text("Đường cao xuống mặt phẳng", "Nhập tên điểm đỉnh S:")
        if p_name is None:                  # Cancel -> thoát im lặng
            return
        p_name = p_name.strip()
        s_id = self._find_point(p_name)
        if not s_id:
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy điểm '{p_name}'.")
            return

        pts_str = self._input_text("Mặt phẳng đáy", "Nhập tên các điểm mặt phẳng (cách nhau dấu cách, ví dụ: M N A B hoặc A B C):")
        if pts_str is None:                 # Cancel -> thoát im lặng
            return
        pts_str = pts_str.split()
        plane_pt_ids = [self._find_point(x) for x in pts_str]
        if len(plane_pt_ids) < 3 or any(pid is None for pid in plane_pt_ids):
            QMessageBox.warning(self, "Lỗi", "Cần nhập ít nhất 3 điểm hợp lệ để tạo mặt phẳng.")
            return
        h_id, sh_id = gen_altitude_to_plane(self.scene, s_id, plane_pt_ids, name="H")
        self._refresh_tree()
        self.viewport.update()
    def add_altitude_to_line(self) -> None:
        """Hạ đường cao SH xuống đoạn thẳng AB"""
        p_name = self._input_text("Đường cao xuống đường thẳng", "Nhập tên điểm đỉnh S:")
        if p_name is None:                  # Cancel -> thoát im lặng
            return
        p_name = p_name.strip()
        s_id = self._find_point(p_name)
        if not s_id:
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy điểm '{p_name}'.")
            return
            
        pts = self._ask_points(2, "Chọn đường thẳng AB")
        if not pts:
            return
        h_id, sh_id = gen_altitude_to_line(self.scene, s_id, pts[0], pts[1], name="H")
        self._refresh_tree()
        self.viewport.update()
    def add_angle_bisector(self) -> None:
        """Dựng đường phân giác góc B qua 3 điểm A B C"""
        pts = self._ask_points(3, "Đường phân giác (A - Đỉnh B - C)")
        if not pts:
            return
        d_id, bd_id = gen_angle_bisector(self.scene, pts[0], pts[1], pts[2], name="D")
        self._refresh_tree()
        self.viewport.update()
    def add_plane_from_points(self) -> None:
        """Dựng mặt phẳng qua các điểm bất kỳ"""
        raw = self._input_text("Mặt phẳng", "Nhập tên các điểm qua mặt phẳng (ví dụ: A B C hoặc M N A B):")
        if raw is None:                     # Cancel -> thoát im lặng
            return
        pts_str = raw.split()
        pt_ids = [self._find_point(x) for x in pts_str]
        if len(pt_ids) < 3 or any(pid is None for pid in pt_ids):
            QMessageBox.warning(self, "Lỗi", "Cần ít nhất 3 điểm hợp lệ.")
            return
        gen_plane_through_points(self.scene, pt_ids, name="mp")
        self._refresh_tree()
        self.viewport.update()
    def add_perp_bisector_plane(self) -> None:
        """Dựng mặt phẳng trung trực của đoạn AB"""
        pts = self._ask_points(2, "Mặt phẳng trung trực đoạn thẳng AB")
        if not pts:
            return
        gen_perp_bisector_segment(self.scene, pts[0], pts[1], name="M")
        self._refresh_tree()
        self.viewport.update()

  
    