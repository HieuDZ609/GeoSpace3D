"""Cua so chinh: toolbar, cay layer, panel thuoc tinh, undo/redo, animation."""
import os
import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (QColorDialog, QDockWidget, QDoubleSpinBox, QFileDialog,
                             QHBoxLayout, QInputDialog, QLabel, QMainWindow,
                             QMessageBox, QPushButton, QSlider, QToolBar, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from core.generators import (gen_angle, gen_box, gen_cone, gen_cube, gen_cylinder,
                             gen_distance, gen_divide, gen_midpoint, gen_on_segment,
                             gen_pyramid, gen_prism, gen_sphere, gen_symmetric)
from core.scene import Obj, Scene
from gui.dialogs import AddPointDialog, CreateSolidDialog
from gui.viewport import Viewport

GROUPS = ["Điểm", "Đoạn thẳng", "Mặt", "Khối", "Mặt cong", "Số đo", "Khác"]
GROUP_MAP = {
    "Points": "Điểm", "Segments": "Đoạn thẳng", "Faces": "Mặt",
    "Solids": "Khối", "Surfaces": "Mặt cong", "Measures": "Số đo",
    "Other": "Khác",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeoSpace 3D - Demo")
        self.resize(1320, 820)
        self.scene = Scene()
        self.scene.on_change(self._on_scene_changed)
        self.current_file = None
        self._refreshing = False

        self.viewport = Viewport()
        self.viewport.set_scene(self.scene)
        self.viewport.objectClicked.connect(self._on_viewport_click)
        self.setCentralWidget(self.viewport)
        self.viewport.setFocus()

        self._build_toolbar()
        self._build_docks()
        self._build_anim()
        self._refresh_tree()
        self.statusBar().showMessage(
            "Chuột trái: xoay 360° | Lăn chuột: zoom | Chuột phải: pan | "
            "Home: reset | 5: phối cảnh song song")
        # Hinh khoi tao: chop S.ABCD + M, N trung diem + doan MN
        self.load_sample()

    # ---------------- toolbar ----------------
    def _build_toolbar(self):
        # Hai hang de hien du cac nut
        tb = QToolBar("Công cụ 1")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb2 = QToolBar("Công cụ 2")
        tb2.setMovable(False)
        self.addToolBar(tb2)

        def act(bar, name, cb, sc=None):
            a = QAction(name, self)
            if sc:
                a.setShortcut(sc)
            a.triggered.connect(cb)
            bar.addAction(a)
            return a

        # Hang 1: file + undo/redo + cong cu diem
        act(tb, "Mới", self.new_project, "Ctrl+N")
        act(tb, "Mở", self.open_project, "Ctrl+O")
        act(tb, "Lưu", self.save_project, "Ctrl+S")
        act(tb, "Xuất ảnh", self.export_png)
        tb.addSeparator()
        act(tb, "Hoàn tác", self.do_undo, "Ctrl+Z")
        act(tb, "Làm lại", self.do_redo, "Ctrl+Y")
        tb.addSeparator()
        act(tb, "Điểm", self.add_point)
        act(tb, "Trung điểm", self.add_midpoint)
        act(tb, "Điểm trên cạnh", self.add_on_segment)
        act(tb, "Chia đoạn", self.add_divide)
        act(tb, "Đối xứng", self.add_symmetry)
        act(tb, "Đoạn thẳng", self.add_segment)
        act(tb, "Mặt", self.add_face)

        # Hang 2: khoi + do dac + animation
        act(tb2, "Lập phương", lambda: self.create_solid("cube"))
        act(tb2, "Hộp chữ nhật", lambda: self.create_solid("box"))
        act(tb2, "Hình chóp", lambda: self.create_solid("pyramid"))
        act(tb2, "Lăng trụ", lambda: self.create_solid("prism"))
        act(tb2, "Hình trụ", lambda: self.create_solid("cylinder"))
        act(tb2, "Hình nón", lambda: self.create_solid("cone"))
        act(tb2, "Hình cầu", lambda: self.create_solid("sphere"))
        tb2.addSeparator()
        act(tb2, "Khoảng cách", self.add_distance)
        act(tb2, "Góc", self.add_angle)
        tb2.addSeparator()
        self.act_rotate = QAction("Tự xoay", self)
        self.act_rotate.setCheckable(True)
        self.act_rotate.triggered.connect(self.toggle_rotate)
        tb2.addAction(self.act_rotate)

    # ---------------- docks ----------------
    def _build_docks(self):
        dw = QDockWidget("Quản lý đối tượng", self)
        dw.setMinimumWidth(280)
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
        self.spins = []
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
        tv.addWidget(QLabel("t (diem chay tren canh)"))
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

    def _build_anim(self):
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self._phase = 0.0

    # ---------------- selection / refresh ----------------
    def _selected_id(self):
        it = self.tree.currentItem()
        if it is None:
            return None
        return it.data(0, Qt.ItemDataRole.UserRole)

    def _on_scene_changed(self, ids):
        self._refresh_tree()
        self.viewport.update()
        sel = self._selected_id()
        if sel and sel in self.scene.objects:
            self._load_props(sel)

    def _refresh_tree(self):
        prev = self._selected_id()
        self._refreshing = True
        self.tree.blockSignals(True)
        self.tree.clear()
        groups = {}
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
            it.setCheckState(0, Qt.CheckState.Checked if o.visible
                             else Qt.CheckState.Unchecked)
            it.setForeground(0, QColor.fromRgbF(*o.color[:3]))
            groups[g].addChild(it)
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self._refreshing = False
        if prev and prev in self.scene.objects:
            self._select_tree_item(prev)

    def _on_tree_select(self):
        oid = self._selected_id()
        self.viewport.selected_id = oid
        self.viewport.update()
        if oid:
            self._load_props(oid)

    def _on_item_changed(self, item, col):
        if self._refreshing or col != 0:
            return
        oid = item.data(0, Qt.ItemDataRole.UserRole)
        if not oid or oid not in self.scene.objects:
            return
        vis = item.checkState(0) == Qt.CheckState.Checked
        o = self.scene.objects[oid]
        if o.visible != vis:
            # KHONG rebuild cay ngay trong signal itemChanged (Qt se xoa item
            # dang duoc xu ly). Chi cap nhat scene + viewport.
            self.scene._push()
            o.visible = vis
            self.scene.evaluate()
            self.viewport.update()
            self.statusBar().showMessage(
                f"{'Hien' if vis else 'An'}: {o.name}", 2000)

    def _load_props(self, oid):
        o = self.scene.objects.get(oid)
        if not o:
            return
        self.prop_name.setText(f"<b>{o.name}</b> &nbsp;({o.kind})&nbsp; [{o.id}]")
        self.btn_vis.setText("Ẩn" if o.visible else "Hiện")
        self.sl_alpha.blockSignals(True)
        self.sl_alpha.setValue(int(255 * (o.color[3] if len(o.color) > 3 else 1.0) / 2.55))
        self.sl_alpha.blockSignals(False)
        if o.kind == "point" and o.ctor == "fixed":
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
            self.sl_t.setValue(int(float(o.args.get("t", 0.5)) * 1000))
            self.sl_t.blockSignals(False)
        else:
            self.t_box.hide()

    def _coord_changed(self):
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects.get(oid)
        if not o or o.kind != "point" or o.ctor != "fixed":
            return
        xyz = [self.spins[i].value() for i in range(3)]
        o.args = {"xyz": xyz}
        self.scene.update(oid, args={"xyz": xyz})

    def _t_changed(self):
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects.get(oid)
        if not o or o.ctor != "on_segment":
            return
        o.args["t"] = self.sl_t.value() / 1000.0
        self.scene._notify([oid])

    def _alpha_changed(self, val):
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        c = list(o.color)
        while len(c) < 4:
            c.append(1.0)
        c[3] = val / 100.0
        self.scene.update(oid, history=False, color=tuple(c))

    def toggle_visible(self):
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        self.scene.update(oid, visible=not o.visible)

    def change_color(self):
        oid = self._selected_id()
        if not oid:
            return
        o = self.scene.objects[oid]
        c = QColorDialog.getColor(QColor.fromRgbF(*o.color[:3]))
        if c.isValid():
            alpha = o.color[3] if len(o.color) > 3 else 1.0
            self.scene.update(oid, color=(c.redF(), c.greenF(), c.blueF(), alpha))

    def _on_viewport_click(self, oid):
        if oid:
            self._select_tree_item(oid)

    def _select_tree_item(self, oid):
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                ch = parent.child(j)
                if ch.data(0, Qt.ItemDataRole.UserRole) == oid:
                    self.tree.setCurrentItem(ch)
                    return

    # ---------------- context menu ----------------
    def _tree_menu(self, pos):
        it = self.tree.itemAt(pos)
        if it is None:
            return
        oid = it.data(0, Qt.ItemDataRole.UserRole)
        if not oid:
            return
        self.tree.setCurrentItem(it)
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction("Rename", lambda: self.rename_object(oid))
        m.addAction("Color", self.change_color)
        m.addAction("Hide/Show", self.toggle_visible)
        m.addSeparator()
        m.addAction("Delete", self.delete_selected)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def rename_object(self, oid):
        o = self.scene.objects[oid]
        name, ok = QInputDialog.getText(self, "Rename", "Ten moi:", text=o.name)
        if ok and name.strip():
            self.scene.update(oid, name=name.strip())

    # ---------------- actions ----------------
    def add_point(self):
        dlg = AddPointDialog(self)
        if dlg.exec():
            name, xyz = dlg.get()
            oid = self.scene.new_id("p")
            self.scene.add(Obj(oid, "point", name, "fixed", {"xyz": list(xyz)},
                               group="Points"))

    def add_midpoint(self):
        ids = self._ask_points(2, "Chọn 2 điểm để lấy trung điểm")
        if not ids:
            return
        name, ok = QInputDialog.getText(
            self, "Tên trung điểm", "Đặt tên (để trống = tự đặt):", text="")
        name = name.strip() if ok and name.strip() else None
        gen_midpoint(self.scene, ids[0], ids[1], name=name)

    def add_on_segment(self):
        ids = self._ask_points(2, "Chọn 2 điểm (điểm chạy trên đoạn)")
        if not ids:
            return
        t = random.uniform(0.15, 0.85)
        gen_on_segment(self.scene, ids[0], ids[1], t=t)

    def add_divide(self):
        ids = self._ask_points(2, "Chọn A, B để chia đoạn")
        if not ids:
            return
        m, ok = QInputDialog.getInt(self, "Ti le", "AM:MB = m:n, nhap m:", 1, 1, 100)
        if not ok:
            return
        n, ok = QInputDialog.getInt(self, "Ti le", "nhap n:", 1, 1, 100)
        if not ok:
            return
        gen_divide(self.scene, ids[0], ids[1], m, n)

    def add_symmetry(self):
        ids = self._ask_points(2, "Chọn điểm A và tâm đối xứng O")
        if ids:
            gen_symmetric(self.scene, ids[0], ids[1])

    def add_segment(self):
        ids = self._ask_points(2, "Chọn 2 điểm để vẽ đoạn thẳng")
        if not ids:
            return
        a, b = ids
        nm = self.scene.objects[a].name + self.scene.objects[b].name
        oid = self.scene.new_id("s")
        self.scene.add(Obj(oid, "segment", nm, "segment", {"a": a, "b": b},
                           group="Segments"))

    def add_face(self):
        names = QInputDialog.getText(
            self, "Mat phang", "Nhap ten cac diem cach nhau boi dau cach (>=3):")[0].split()
        ids = [self._find_point(n) for n in names]
        if len(ids) < 3 or any(i is None for i in ids):
            QMessageBox.warning(self, "Loi", "Khong tim thay du 3 diem.")
            return
        oid = self.scene.new_id("f")
        self.scene.add(Obj(oid, "face", "".join(names), "face", {"pts": ids},
                           color=(0.5, 0.7, 1.0, 0.35), group="Faces"))

    def add_distance(self):
        ids = self._ask_points(2, "Chọn 2 điểm để đo khoảng cách")
        if ids:
            gen_distance(self.scene, ids[0], ids[1])

    def add_angle(self):
        ids = self._ask_points(3, "Chọn A, đỉnh B, C để đo góc ∠ABC")
        if ids:
            gen_angle(self.scene, ids[0], ids[1], ids[2])

    def create_solid(self, kind):
        dlg = CreateSolidDialog(self, kind)
        if not dlg.exec():
            return
        p = dlg.get()
        if kind == "cube":
            gen_cube(self.scene, p["A"], p["edge"])
        elif kind == "box":
            gen_box(self.scene, p["A"], p["dx"], p["dy"], p["dz"])
        elif kind == "pyramid":
            gen_pyramid(self.scene, p["side"], p["height"])
        elif kind == "prism":
            gen_prism(self.scene, p["side"], p["height"])
        elif kind == "cylinder":
            gen_cylinder(self.scene, p["A"], p["side"], p["height"])
        elif kind == "cone":
            gen_cone(self.scene, p["A"], p["side"], p["height"])
        elif kind == "sphere":
            gen_sphere(self.scene, p["A"], p["side"])

    def delete_selected(self):
        oid = self._selected_id()
        if not oid:
            return
        removed = self.scene.remove(oid)
        if len(removed) > 1:
            QMessageBox.information(
                self, "Xoa", f"Da xoa {len(removed)} doi tuong (kem phu thuoc).")

    # ---------------- animation ----------------
    def toggle_rotate(self):
        self._rotate_on = getattr(self, "_rotate_on", False)
        self._rotate_on = self.act_rotate.isChecked()
        self._sync_timer()

    def toggle_anim(self):
        self._anim_on = self.act_anim.isChecked()
        self._sync_timer()

    def _sync_timer(self):
        if getattr(self, "_rotate_on", False) or getattr(self, "_anim_on", False):
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self):
        import math
        self._phase += 0.06
        if getattr(self, "_rotate_on", False):
            self.viewport.yaw += 0.6
        if getattr(self, "_anim_on", False):
            for o in self.scene.objects.values():
                if o.ctor == "on_segment":
                    o.args["t"] = 0.5 + 0.5 * math.sin(self._phase)
            self.scene.evaluate()
        self.viewport.update()

    # ---------------- file ----------------
    def new_project(self):
        self.scene = Scene()
        self.scene.on_change(self._on_scene_changed)
        self.viewport.set_scene(self.scene)
        self.current_file = None
        self.setWindowTitle("GeoSpace 3D - Demo")
        self._refresh_tree()
        self.viewport.update()

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mo", "", "JSON (*.json)")
        if not path:
            return
        self.scene = Scene.load(path)
        self.scene.on_change(self._on_scene_changed)
        self.viewport.set_scene(self.scene)
        self.current_file = path
        self.setWindowTitle(f"GeoSpace 3D - {os.path.basename(path)}")
        self._refresh_tree()
        self.viewport.update()

    def save_project(self):
        if not self.current_file:
            path, _ = QFileDialog.getSaveFileName(self, "Luu", "bai1.json", "JSON (*.json)")
            if not path:
                return
            self.current_file = path
        self.scene.save(self.current_file)
        self.statusBar().showMessage(f"Da luu: {self.current_file}", 4000)
        self.setWindowTitle(f"GeoSpace 3D - {os.path.basename(self.current_file)}")

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Xuat PNG", "hinh.json.png", "PNG (*.png)")
        if not path:
            return
        self.viewport.repaint()
        img = self.viewport.grabFramebuffer()
        img.save(path)
        self.statusBar().showMessage(f"Da xuat: {path}", 4000)

    def do_undo(self):
        if not self.scene.undo():
            self.statusBar().showMessage("Khong con gi de undo", 2000)

    def do_redo(self):
        if not self.scene.redo():
            self.statusBar().showMessage("Khong con gi de redo", 2000)

    # ---------------- sample ----------------
    def load_sample(self):
        self.new_project()
        pts = gen_pyramid(self.scene, 4.0, 5.0)["points"]
        A, B, C, D, S = pts
        M = gen_midpoint(self.scene, S, A, name="M")
        N = gen_midpoint(self.scene, S, C, name="N")
        nm = self.scene.objects[M].name + self.scene.objects[N].name
        oid = self.scene.new_id("s")
        self.scene.add(Obj(oid, "segment", nm, "segment", {"a": M, "b": N},
                           color=(1.0, 0.8, 0.2), group="Segments"))
        gen_distance(self.scene, M, N)
        self.statusBar().showMessage(
            "Mau: chop S.ABCD + M,N la trung diem SA,SC + doan MN", 6000)

    # ---------------- helpers ----------------
    def _ask_points(self, n, title):
        names = QInputDialog.getText(
            self, title, f"Nhap ten {n} diem cach nhau boi dau cach:")[0].split()
        ids = [self._find_point(x) for x in names]
        if len(ids) != n or any(i is None for i in ids):
            QMessageBox.warning(self, "Loi", f"Can dung {n} diem hop le.")
            return None
        return ids

    def _find_point(self, name):
        for o in self.scene.objects.values():
            if o.kind == "point" and o.name == name:
                return o.id
        return None
