"""OpenGL viewport: xoay 4 huong GeoGebra 3D, truc Oxyz co dinh & che do WireFrame/FaceModel."""
from __future__ import annotations

import math

import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FALSE,
    GL_FILL,
    GL_FRONT_AND_BACK,
    GL_LEQUAL,
    GL_LESS,
    GL_LIGHTING,
    GL_LINES,
    GL_LINE_SMOOTH,
    GL_LINE_SMOOTH_HINT,
    GL_LINE_STIPPLE,
    GL_MODELVIEW,
    GL_NICEST,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_POINTS,
    GL_POINT_SMOOTH,
    GL_POLYGON,
    GL_POLYGON_OFFSET_FILL,
    GL_PROJECTION,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TRIANGLES,
    GL_TRUE,
    glBegin,
    glBlendFunc,
    glClear,
    glClearColor,
    glColor3f,
    glColor4f,
    glColorMask,
    glDepthFunc,
    glDepthMask,
    glDisable,
    glEnable,
    glEnd,
    glHint,
    glLineStipple,
    glLineWidth,
    glLoadIdentity,
    glLoadMatrixd,
    glMatrixMode,
    glNormal3dv,
    glPointSize,
    glPolygonMode,
    glPolygonOffset,
    glVertex3dv,
    glVertex3f,
    glViewport,
)
from OpenGL.GL import GL_COMPILE, GL_LINE_LOOP, GL_QUADS, glCallList, glEndList, glGenLists, glNewList
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from core.geometry import (
    FaceModel,
    MeasureData,
    Node,
    RGBA,
    SegmentData,
    SolidModel,
    WireFrame,
)
from core.math3d import (
    Mat4,
    look_at_matrix,
    normal_of_points,
    ortho_matrix,
    perspective_matrix,
    project_to_screen,
    vec3,
)
from core.scene import Scene

# ---------------- giao dien sang (kieu GeoGebra 3D) ----------------
BG = (1.0, 1.0, 1.0)                  # nen trang
AX_X = (0.86, 0.08, 0.08)             # Ox do
AX_Y = (0.04, 0.55, 0.10)             # Oy xanh la
AX_Z = (0.08, 0.10, 0.88)             # Oz xanh duong
AXIS_LEN = 10                         # do dai nua truc (don vi)
HIGHLIGHT = (1.0, 0.55, 0.0)          # mau doi tuong dang chon
PLANE_HALF = 12.0                     # nua canh mat phang nen


def _luma(c) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def on_light(c, alpha: float | None = None) -> RGBA:
    """Dam mau lai neu qua sang (vd. trang/vang nhat) de noi bat tren nen trang."""
    r, g, b = c[0], c[1], c[2]
    l = _luma(c)
    if l > 0.55:
        k = 0.45 / l
        r, g, b = r * k, g * k, b * k
    return (r, g, b, c[3] if alpha is None else alpha)


def darker(c, k: float = 0.45, alpha: float = 1.0) -> RGBA:
    return (c[0] * k, c[1] * k, c[2] * k, alpha)


def _qc(c) -> QColor:
    return QColor.fromRgbF(c[0], c[1], c[2])


class Viewport(QOpenGLWidget):
    objectClicked = pyqtSignal(str)     # id doi tuong duoc chon hoac ""
    viewStateChanged = pyqtSignal()     # phat khi doi lock_origin / ortho / display_mode

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene: Scene | None = None
        # Goc nhin mac dinh kieu GeoGebra 3D: +X do huong trai-duoi, +Y xanh la phai-duoi, +Z thang dung
        self.yaw: float = -50.0
        self.pitch: float = 24.0
        self.dist: float = 22.0
        self.target: list[float] = [0.0, 0.0, 0.0]

        self.ortho: bool = False
        self.lock_origin: bool = True         # Co dinh goc O(0,0,0) o tam khung nhin
        self.display_mode: str = "solid"      # "solid" (Mat + Khung) | "wireframe" | "face"
        self.show_grid: bool = False          # luoi o ke tren mat phang nen
        self.show_plane: bool = True          # mat phang Oxy xam mo nhu GeoGebra
        self._plane_list = None               # display list cua mat phang nen
        self.show_labels: bool = True
        self.show_corner_axes: bool = True    # Cum truc Oxyz co dinh o goc duoi-trai

        self._last = None
        self._mode: str | None = None
        self._mv: Mat4 | None = None
        self._proj: Mat4 | None = None
        self._vp: tuple[int, int, int, int] = (0, 0, 1, 1)
        self.selected_id: str | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ---------------- setup ----------------
    def set_scene(self, scene: Scene) -> None:
        self.scene = scene
        self.update()

    def set_lock_origin(self, locked: bool) -> None:
        self.lock_origin = locked
        if locked:
            self.target = [0.0, 0.0, 0.0]
        self.viewStateChanged.emit()
        self.update()

    def set_ortho(self, ortho: bool) -> None:
        self.ortho = ortho
        self.viewStateChanged.emit()
        self.update()

    def set_show_plane(self, on: bool) -> None:
        self.show_plane = on
        self.viewStateChanged.emit()
        self.update()

    def set_show_grid(self, on: bool) -> None:
        self.show_grid = on
        self.viewStateChanged.emit()
        self.update()

    def set_display_mode(self, mode: str) -> None:
        if mode in ("solid", "wireframe", "face"):
            self.display_mode = mode
            self.viewStateChanged.emit()
            self.update()

    def cycle_display_mode(self) -> str:
        modes = ["solid", "wireframe", "face"]
        nxt = modes[(modes.index(self.display_mode) + 1) % len(modes)]
        self.set_display_mode(nxt)
        return nxt

    def initializeGL(self) -> None:
        self._plane_list = None
        glClearColor(*BG, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)

    def resizeGL(self, w: int, h: int) -> None:
        dpr = self.devicePixelRatioF()
        glViewport(0, 0, max(1, int(w * dpr)), max(1, int(h * dpr)))

    def _setup_camera(self) -> None:
        w = max(1, self.width())
        h = max(1, self.height())
        dpr = self.devicePixelRatioF()
        glViewport(0, 0, int(w * dpr), int(h * dpr))
        aspect = w / h

        if self.ortho:
            s = self.dist * 0.5
            self._proj = ortho_matrix(-s * aspect, s * aspect, -s, s, 0.1, 1000.0)
        else:
            self._proj = perspective_matrix(45.0, aspect, 0.1, 1000.0)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixd(self._proj)

        if self.lock_origin:
            self.target = [0.0, 0.0, 0.0]

        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = vec3(
            self.target[0] + self.dist * math.cos(pitch) * math.cos(yaw),
            self.target[1] + self.dist * math.cos(pitch) * math.sin(yaw),
            self.target[2] + self.dist * math.sin(pitch),
        )
        # Vector up luon la (0, 0, 1) -> xoay Turntable quanh Oz, khong bi nghieng truc
        self._mv = look_at_matrix(eye, vec3(*self.target), vec3(0.0, 0.0, 1.0))

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixd(self._mv)

        self._vp = (0, 0, w, h)

    # ---------------- paint ----------------
    def paintGL(self) -> None:
        self._reset_gl_state()
        glClearColor(*BG, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._setup_camera()

        if self.show_plane:
            self._draw_ground_plane()
        if self.show_grid:
            self._draw_grid()
        self._draw_axes()

        if self.scene is not None:
            if self.display_mode in ("solid", "face"):
                self._draw_faces()
            if self.display_mode in ("solid", "wireframe"):
                self._draw_edges()
            self._draw_measures()
            self._draw_points()
            self._draw_selection()

        if self.show_corner_axes:
            self._draw_corner_axes()

        if self.show_labels:
            self._draw_labels()

    def _reset_gl_state(self) -> None:
        """Dat lai trang thai OpenGL sau khi QPainter ve chu o frame truoc."""
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glDepthMask(GL_TRUE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LINE_STIPPLE)
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glLineWidth(1.0)
        glPointSize(9.0)

    def _draw_ground_plane(self) -> None:
        """Mat phang Oxy xam mo, mo dan ve phia mep (giong GeoGebra 3D)."""
        if self._plane_list is None:
            H, N = PLANE_HALF, 20
            step = 2.0 * H / N

            def alpha(x: float, y: float) -> float:
                t = max(0.0, min(1.0, (1.0 - max(abs(x), abs(y)) / H) / 0.55))
                return 0.46 * t * t * (3.0 - 2.0 * t)      # smoothstep

            lst = glGenLists(1)
            glNewList(lst, GL_COMPILE)
            glBegin(GL_QUADS)
            for i in range(N):
                for j in range(N):
                    x0, y0 = -H + i * step, -H + j * step
                    x1, y1 = x0 + step, y0 + step
                    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                        glColor4f(0.45, 0.45, 0.48, alpha(x, y))
                        glVertex3f(x, y, 0.0)
            glEnd()
            glEndList()
            self._plane_list = lst
        glDepthMask(GL_FALSE)       # khong che cac doi tuong nam tren/duoi mat phang
        glCallList(self._plane_list)
        glDepthMask(GL_TRUE)

    def _draw_grid(self) -> None:
        glColor4f(0.35, 0.37, 0.45, 0.28)
        glLineWidth(1.0)
        glDepthMask(GL_FALSE)
        glBegin(GL_LINES)
        n = int(AXIS_LEN)
        for i in range(-n, n + 1):
            if i == 0:
                continue
            glVertex3f(i, -n, 0); glVertex3f(i, n, 0)
            glVertex3f(-n, i, 0); glVertex3f(n, i, 0)
        glEnd()
        glDepthMask(GL_TRUE)

    def _draw_axes(self) -> None:
        """He truc Oxyz: Ox do, Oy xanh la, Oz xanh duong; phan am net dut, cham tron chia don vi."""
        L = float(AXIS_LEN)
        axes = (
            (AX_X, (1.0, 0.0, 0.0)),
            (AX_Y, (0.0, 1.0, 0.0)),
            (AX_Z, (0.0, 0.0, 1.0)),
        )

        # 1) Phan am (net dut, nhat hon)
        glEnable(GL_LINE_STIPPLE)
        glLineStipple(3, 0x5555)
        glLineWidth(1.4)
        glBegin(GL_LINES)
        for col, d in axes:
            glColor4f(col[0], col[1], col[2], 0.65)
            glVertex3f(-L * d[0], -L * d[1], -L * d[2]); glVertex3f(0, 0, 0)
        glEnd()
        glDisable(GL_LINE_STIPPLE)

        # 2) Phan duong (lien, dam)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        for col, d in axes:
            glColor3f(*col)
            glVertex3f(0, 0, 0); glVertex3f(L * d[0], L * d[1], L * d[2])
        glEnd()

        # 3) Cham tron chia don vi tren moi truc
        glPointSize(5.0)
        glBegin(GL_POINTS)
        for col, d in axes:
            glColor3f(*col)
            for i in range(-int(L), int(L) + 1):
                if i == 0:
                    continue
                glVertex3f(i * d[0], i * d[1], i * d[2])
        glEnd()

        # 4) Mui ten 3D o +X, +Y, +Z
        a_len, a_rad = 0.55, 0.16
        glBegin(GL_TRIANGLES)
        glColor3f(*AX_X)
        glVertex3f(L + a_len, 0, 0); glVertex3f(L, -a_rad, 0); glVertex3f(L, a_rad, 0)
        glVertex3f(L + a_len, 0, 0); glVertex3f(L, 0, -a_rad); glVertex3f(L, 0, a_rad)
        glColor3f(*AX_Y)
        glVertex3f(0, L + a_len, 0); glVertex3f(-a_rad, L, 0); glVertex3f(a_rad, L, 0)
        glVertex3f(0, L + a_len, 0); glVertex3f(0, L, -a_rad); glVertex3f(0, L, a_rad)
        glColor3f(*AX_Z)
        glVertex3f(0, 0, L + a_len); glVertex3f(-a_rad, 0, L); glVertex3f(a_rad, 0, L)
        glVertex3f(0, 0, L + a_len); glVertex3f(0, -a_rad, L); glVertex3f(0, a_rad, L)
        glEnd()
        glLineWidth(1.0)
        glPointSize(9.0)

    def _corner_gizmo_matrices(self) -> tuple[tuple[int, int, int, int], Mat4, Mat4]:
        """Ma tran cho cum truc Oxyz co dinh o goc duoi-trai man hinh."""
        vp = (14, 14, 104, 104)
        proj = ortho_matrix(-1.55, 1.55, -1.55, 1.55, 0.1, 10.0)
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = vec3(
            3.0 * math.cos(pitch) * math.cos(yaw),
            3.0 * math.cos(pitch) * math.sin(yaw),
            3.0 * math.sin(pitch),
        )
        mv = look_at_matrix(eye, vec3(0.0, 0.0, 0.0), vec3(0.0, 0.0, 1.0))
        return vp, mv, proj

    def _draw_corner_axes(self) -> None:
        """Ve cum truc Oxyz luon co dinh o goc duoi-trai man hinh."""
        if self._mv is None or self._proj is None:
            return
        vp, mv, proj = self._corner_gizmo_matrices()
        dpr = self.devicePixelRatioF()
        glViewport(int(vp[0] * dpr), int(vp[1] * dpr), int(vp[2] * dpr), int(vp[3] * dpr))
        glClear(GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixd(proj)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixd(mv)

        glLineWidth(2.2)
        glBegin(GL_LINES)
        glColor3f(*AX_X); glVertex3f(0, 0, 0); glVertex3f(1.05, 0, 0)
        glColor3f(*AX_Y); glVertex3f(0, 0, 0); glVertex3f(0, 1.05, 0)
        glColor3f(*AX_Z); glVertex3f(0, 0, 0); glVertex3f(0, 0, 1.05)
        glEnd()

        glPointSize(6.0)
        glBegin(GL_POINTS)
        glColor3f(0.25, 0.25, 0.30); glVertex3f(0, 0, 0)
        glEnd()

        # Khoi phuc lai viewport va ma tran chinh
        glViewport(0, 0, int(self._vp[2] * dpr), int(self._vp[3] * dpr))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixd(self._proj)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixd(self._mv)
        glLineWidth(1.0)
        glPointSize(9.0)

    def _visible(self, kinds: list[str] | None = None) -> list[Node]:
        if self.scene is None:
            return []
        out: list[Node] = []
        for o in self.scene.objects.values():
            if not o.visible or o.value is None:
                continue
            if kinds and o.kind not in kinds:
                continue
            out.append(o)
        return out

    def _draw_faces(self) -> None:
        glDepthMask(GL_TRUE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)

        # Khi o che do chi mat ("face"), tang nhe do dam mau de de nhin hon
        boost_alpha = (self.display_mode == "face")

        for o in self._visible():
            if o.kind == "solid":
                continue
            val = o.value
            col = o.color
            if boost_alpha:
                col = (col[0], col[1], col[2], min(0.95, max(0.55, col[3] + 0.30)))

            if isinstance(val, FaceModel):
                self._gl_face_model(val, col)
            elif isinstance(val, SolidModel):
                self._gl_face_model(val.face_model, col)

        glDisable(GL_POLYGON_OFFSET_FILL)

    def _gl_face_model(self, model: FaceModel, color: RGBA) -> None:
        glColor4f(*color)
        for face_indices in model.faces:
            if len(face_indices) < 3:
                continue
            p0 = model.vertices[face_indices[0]]
            p1 = model.vertices[face_indices[1]]
            p2 = model.vertices[face_indices[2]]
            n = normal_of_points(p0, p1, p2)
            glBegin(GL_POLYGON)
            glNormal3dv(n)
            for idx in face_indices:
                glVertex3dv(model.vertices[idx])
            glEnd()

    def _iter_lines(self):
        for o in self._visible():
            if o.kind == "solid":
                continue
            val = o.value
            if isinstance(val, SegmentData):
                yield val.a, val.b, on_light(o.color, 1.0)
            elif isinstance(val, WireFrame):
                edge_col = darker(o.color, 0.5, 0.85)
                for i0, i1 in val.edges:
                    yield val.vertices[i0], val.vertices[i1], edge_col
            elif isinstance(val, SolidModel):
                wf = val.wireframe
                edge_col = darker(o.color, 0.5, 0.85)
                for i0, i1 in wf.edges:
                    yield wf.vertices[i0], wf.vertices[i1], edge_col

    def _draw_edges(self) -> None:
        lines = list(self._iter_lines())

        # 1) Net dut: tat ca canh (ke ca bi che khuat)
        glDepthMask(GL_FALSE)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_LINE_STIPPLE)
        glLineStipple(2, 0xAAAA)
        glLineWidth(1.0)
        glColor4f(0.35, 0.38, 0.50, 0.60)
        glBegin(GL_LINES)
        for a, b, _ in lines:
            glVertex3dv(a); glVertex3dv(b)
        glEnd()
        glDisable(GL_LINE_STIPPLE)

        # 2) Net lien: chi ve phan canh nhin thay truoc Z-buffer
        glDepthFunc(GL_LESS)
        glLineWidth(1.6)
        glBegin(GL_LINES)
        for a, b, col in lines:
            glColor4f(col[0], col[1], col[2], col[3])
            glVertex3dv(a); glVertex3dv(b)
        glEnd()

        glDepthFunc(GL_LEQUAL)
        glDepthMask(GL_TRUE)
        glLineWidth(1.0)

    def _draw_measures(self) -> None:
        """Ve doan noi cua so do khoang cach (hien thi o moi che do)."""
        glDepthMask(GL_FALSE)
        glLineWidth(1.4)
        glBegin(GL_LINES)
        glColor4f(0.85, 0.45, 0.0, 1.0)
        for o in self._visible(["measure"]):
            if isinstance(o.value, MeasureData) and o.value.segment is not None:
                glVertex3dv(o.value.segment.a)
                glVertex3dv(o.value.segment.b)
        glEnd()
        glDepthMask(GL_TRUE)
        glLineWidth(1.0)

    def _draw_points(self) -> None:
        """Diem: cham mau co vien toi de noi bat tren nen sang."""
        pts = [o for o in self._visible(["point"]) if isinstance(o.value, np.ndarray)]

        # Quang sang quanh diem dang chon
        sel = next((o for o in pts if o.id == self.selected_id), None)
        if sel is not None:
            glPointSize(19.0)
            glColor4f(HIGHLIGHT[0], HIGHLIGHT[1], HIGHLIGHT[2], 0.55)
            glBegin(GL_POINTS)
            glVertex3dv(sel.value)
            glEnd()

        # 1) vien toi
        glPointSize(11.0)
        glColor4f(0.05, 0.07, 0.18, 0.95)
        glBegin(GL_POINTS)
        for o in pts:
            glVertex3dv(o.value)
        glEnd()

        # 2) ruot mau
        glPointSize(7.5)
        glBegin(GL_POINTS)
        for o in pts:
            c = on_light(o.color, 1.0)
            glColor4f(*c)
            glVertex3dv(o.value)
        glEnd()
        glPointSize(9.0)

    def _draw_selection(self) -> None:
        """To sang doan / mat / khoi / mat cong dang duoc chon (diem da co quang rieng)."""
        if self.scene is None or not self.selected_id:
            return
        o = self.scene.objects.get(self.selected_id)
        if o is None or not o.visible or o.value is None or o.kind in ("point", "measure"):
            return
        val = o.value
        glDisable(GL_DEPTH_TEST)
        glColor4f(HIGHLIGHT[0], HIGHLIGHT[1], HIGHLIGHT[2], 0.95)
        if isinstance(val, SegmentData):
            glLineWidth(4.0)
            glBegin(GL_LINES)
            glVertex3dv(val.a); glVertex3dv(val.b)
            glEnd()
        else:
            fm = None
            edges: list[tuple[np.ndarray, np.ndarray]] = []
            if isinstance(val, FaceModel):
                fm = val
            elif isinstance(val, SolidModel):
                fm = val.face_model
                edges = [(val.wireframe.vertices[i], val.wireframe.vertices[j])
                         for i, j in val.wireframe.edges]
            elif isinstance(val, WireFrame):
                edges = [(val.vertices[i], val.vertices[j]) for i, j in val.edges]
            if fm is not None:
                glColor4f(HIGHLIGHT[0], HIGHLIGHT[1], HIGHLIGHT[2], 0.30)
                for f in fm.faces:
                    if len(f) >= 3:
                        glBegin(GL_POLYGON)
                        for idx in f:
                            glVertex3dv(fm.vertices[idx])
                        glEnd()
                if isinstance(val, FaceModel):
                    glColor4f(HIGHLIGHT[0], HIGHLIGHT[1], HIGHLIGHT[2], 0.95)
                    glLineWidth(3.0)
                    for f in fm.faces:
                        glBegin(GL_LINE_LOOP)
                        for idx in f:
                            glVertex3dv(fm.vertices[idx])
                        glEnd()
            if edges:
                glColor4f(HIGHLIGHT[0], HIGHLIGHT[1], HIGHLIGHT[2], 0.95)
                glLineWidth(2.5)
                glBegin(GL_LINES)
                for a, b in edges:
                    glVertex3dv(a); glVertex3dv(b)
                glEnd()
        glEnable(GL_DEPTH_TEST)
        glLineWidth(1.0)

    # ---------------- overlay text ----------------
    @staticmethod
    def _text_halo(p: QPainter, x: int, y: int, text: str, color: QColor) -> None:
        """Chu co vien trang mong de doc duoc tren moi nen."""
        p.setPen(QColor(255, 255, 255, 235))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p.drawText(x + dx, y + dy, text)
        p.setPen(color)
        p.drawText(x, y, text)

    def _draw_labels(self) -> None:
        if self._mv is None or self._proj is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        L = float(AXIS_LEN)

        f_small = QFont(self.font()); f_small.setPointSize(8)
        f_axis = QFont(self.font()); f_axis.setPointSize(11); f_axis.setBold(True)
        f_name = QFont(self.font()); f_name.setPointSize(10); f_name.setBold(True)
        qx, qy, qz = _qc(AX_X), _qc(AX_Y), _qc(AX_Z)

        # 1) Ten 3 truc chinh x, y, z
        p.setFont(f_axis)
        for pt, label, col in [
            (vec3(L + 1.2, 0.0, 0.0), "x", qx),
            (vec3(0.0, L + 1.2, 0.0), "y", qy),
            (vec3(0.0, 0.0, 8.3), "z", qz),
        ]:
            proj = project_to_screen(pt, self._mv, self._proj, self._vp)
            if proj and 0.0 <= proj[2] <= 1.0:
                p.setPen(col)
                p.drawText(int(proj[0]) - 4, int(proj[1]) + 5, label)

        # 2) So chia don vi tren cac truc
        p.setFont(f_small)
         # So tren truc X
        for i in range(-int(L), int(L) + 1):
            if i == 0: continue
            proj = project_to_screen(vec3(i, 0, 0), self._mv, self._proj, self._vp)
            if proj and 0.0 <= proj[2] <= 1.0:
                p.setPen(qx)
                p.drawText(int(proj[0]) - 6, int(proj[1]) + 15, str(i))
        # So tren truc Y
        for i in range(-int(L), int(L) + 1):
            if i == 0: continue
            proj = project_to_screen(vec3(0, i, 0), self._mv, self._proj, self._vp)
            if proj and 0.0 <= proj[2] <= 1.0:
                p.setPen(qy)
                p.drawText(int(proj[0]) - 15, int(proj[1]) - 4, str(i))
        # So tren truc Z
        for i in range(-4, 8):
            if i == 0: continue
            proj = project_to_screen(vec3(0, 0, i), self._mv, self._proj, self._vp)
            if proj and 0.0 <= proj[2] <= 1.0:
                p.setPen(qz)
                p.drawText(int(proj[0]) - 16, int(proj[1]) + 4, str(i))

        # 3) Nhan x, y, z tren cum truc co dinh o goc man hinh
        if self.show_corner_axes:
            p.setFont(f_axis)
            g_vp, g_mv, g_proj = self._corner_gizmo_matrices()
            h_win = self.height()
            for pt, label, col in [
                (vec3(1.28, 0.0, 0.0), "x", qx),
                (vec3(0.0, 1.28, 0.0), "y", qy),
                (vec3(0.0, 0.0, 1.28), "z", qz),
            ]:
                local_proj = project_to_screen(pt, g_mv, g_proj, (g_vp[0], 0, g_vp[2], g_vp[3]))
                if local_proj:
                    sx = local_proj[0]
                    sy = h_win - g_vp[1] - (g_vp[3] - local_proj[1])
                    p.setPen(col)
                    p.drawText(int(sx) - 3, int(sy) + 5, label)

        # 4) Ten diem va so do trong scene
        p.setFont(f_name)
        if self.scene is not None:
            for o in self.scene.objects.values():
                if not o.visible or o.value is None:
                    continue
                if o.kind == "point" and isinstance(o.value, np.ndarray):
                    pt = o.value
                    text = o.name
                    color = QColor(15, 25, 70)
                    off = (8, -6)
                elif o.kind == "measure" and isinstance(o.value, MeasureData):
                    pt = o.value.anchor
                    text = o.value.text
                    color = QColor(180, 85, 0)
                    off = (8, -10)
                else:
                    continue

                proj = project_to_screen(pt, self._mv, self._proj, self._vp)
                if proj is None:
                    continue
                sx, sy, sz = proj
                if sz < 0.0 or sz > 1.0:
                    continue
                self._text_halo(p, int(sx) + off[0], int(sy) + off[1], text, color)
        p.end()

    # ---------------- mouse & keyboard ----------------
    def mousePressEvent(self, ev) -> None:
        self._last = ev.position()
        shift_held = bool(ev.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if ev.button() == Qt.MouseButton.RightButton:
            self._mode = "rotate"
            self.update()
            return
        
        if ev.button() == Qt.MouseButton.LeftButton and not shift_held:
            picked = self._try_pick(ev.position())
            self.selected_id = picked or None
            self.objectClicked.emit(picked or "")
            self._mode = "rotate"   # Cho phép kéo chuột trái để xoay tự do
            self.update()
        elif (
            ev.button() == Qt.MouseButton.MiddleButton
            or (ev.button() == Qt.MouseButton.LeftButton and shift_held)
        ):
            self._mode = "pan"

    def mouseMoveEvent(self, ev) -> None:
        if self._last is None:
            return
        dx = ev.position().x() - self._last.x()
        dy = ev.position().y() - self._last.y()
        self._last = ev.position()

        if self._mode == "rotate":
            # Xoay 4 huong (trai/phai/len/xuong)
            self.yaw = (self.yaw - dx * 0.30) % 360.0
            self.pitch = max(-89.0, min(89.0, self.pitch - dy * 0.30))
            self.update()
        elif self._mode == "pan" and not self.lock_origin and self._mv is not None:
            k = 0.0018 * self.dist
            right_vec = self._mv[0, :3]
            up_vec = self._mv[1, :3]
            delta = -right_vec * (dx * k) + up_vec * (dy * k)
            self.target[0] += float(delta[0])
            self.target[1] += float(delta[1])
            self.target[2] += float(delta[2])
            self.update()

    def mouseReleaseEvent(self, ev) -> None:
        self._last = None
        self._mode = None

    def wheelEvent(self, ev) -> None:
        d = ev.angleDelta().y()
        self.dist = max(2.0, min(300.0, self.dist * (0.9 if d > 0 else 1.1)))
        self.update()

    def keyPressEvent(self, ev) -> None:
        k = ev.key()
        if k == Qt.Key.Key_Left:
            self.yaw = (self.yaw - 3.0) % 360.0
        elif k == Qt.Key.Key_Right:
            self.yaw = (self.yaw + 3.0) % 360.0
        elif k == Qt.Key.Key_Up:
            self.pitch = min(89.0, self.pitch + 3.0)
        elif k == Qt.Key.Key_Down:
            self.pitch = max(-89.0, self.pitch - 3.0)
        elif k == Qt.Key.Key_L:
            self.set_lock_origin(not self.lock_origin)
            return
        elif k == Qt.Key.Key_M:
            self.cycle_display_mode()
            return
        elif k == Qt.Key.Key_Home:
            self.reset_view()
            return
        elif k == Qt.Key.Key_5:
            self.set_ortho(not self.ortho)
            return
        elif k == Qt.Key.Key_1:
            self.yaw, self.pitch = 0.0, 0.0
        elif k == Qt.Key.Key_2:
            self.yaw, self.pitch = -90.0, 89.0
        elif k == Qt.Key.Key_3:
            self.yaw, self.pitch = 90.0, 0.0
        elif k == Qt.Key.Key_0:
            self.yaw, self.pitch = -50.0, 24.0
        elif not self.lock_origin and self._mv is not None:
            step = self.dist * 0.06
            right_vec = self._mv[0, :3]
            up_vec = self._mv[1, :3]
            if k == Qt.Key.Key_W:
                self.target = list(np.array(self.target) + up_vec * step)
            elif k == Qt.Key.Key_S:
                self.target = list(np.array(self.target) - up_vec * step)
            elif k == Qt.Key.Key_A:
                self.target = list(np.array(self.target) - right_vec * step)
            elif k == Qt.Key.Key_D:
                self.target = list(np.array(self.target) + right_vec * step)
        self.update()

    def reset_view(self) -> None:
        self.yaw, self.pitch, self.dist = -50.0, 24.0, 22.0
        self.target = [0.0, 0.0, 0.0]
        self.ortho = False
        self.display_mode = "solid"
        self.viewStateChanged.emit()
        self.update()

    @staticmethod
    def _dist_point_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    @staticmethod
    def _point_in_polygon(px: float, py: float, poly: list[tuple[float, float]]) -> bool:
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-18) + xi:
                inside = not inside
            j = i
        return inside

    def _try_pick(self, pos) -> str | None:
        """Uu tien: diem > doan thang > mat (mat gan nguoi xem nhat)."""
        if self.scene is None or self._mv is None or self._proj is None:
            return None
        mx, my = pos.x(), pos.y()

        # 1) Diem
        best: str | None = None
        bestd = 12.0
        for o in self.scene.objects.values():
            if not o.visible or o.kind != "point" or not isinstance(o.value, np.ndarray):
                continue
            proj = project_to_screen(o.value, self._mv, self._proj, self._vp)
            if proj is None:
                continue
            sx, sy, sz = proj
            if sz < 0.0 or sz > 1.0:
                continue
            d = math.hypot(sx - mx, sy - my)
            if d < bestd:
                bestd, best = d, o.id
        if best:
            return best

        # 2) Doan thang
        bestd = 7.0
        for o in self.scene.objects.values():
            if not o.visible or o.kind != "segment" or not isinstance(o.value, SegmentData):
                continue
            pa = project_to_screen(o.value.a, self._mv, self._proj, self._vp)
            pb = project_to_screen(o.value.b, self._mv, self._proj, self._vp)
            if pa is None or pb is None or not (0.0 <= pa[2] <= 1.0 and 0.0 <= pb[2] <= 1.0):
                continue
            d = self._dist_point_segment(mx, my, pa[0], pa[1], pb[0], pb[1])
            if d < bestd:
                bestd, best = d, o.id
        if best:
            return best

        # 3) Mat (da giac): diem click nam trong da giac chieu, chon mat gan nhat
        best_z = 2.0
        for o in self.scene.objects.values():
            if not o.visible or o.kind != "face" or not isinstance(o.value, FaceModel):
                continue
            projs = [project_to_screen(v, self._mv, self._proj, self._vp) for v in o.value.vertices]
            if any(q is None or not (0.0 <= q[2] <= 1.0) for q in projs):
                continue
            poly = [(q[0], q[1]) for q in projs]
            if len(poly) >= 3 and self._point_in_polygon(mx, my, poly):
                z = sum(q[2] for q in projs) / len(projs)
                if z < best_z:
                    best_z, best = z, o.id
        return best