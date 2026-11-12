"""OpenGL viewport: camera 360, Oxyz, ve doi tuong tu struct hinh hoc, click chon diem."""
from __future__ import annotations

import math

import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
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
    GL_TRUE,
    GL_FALSE,
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
from PyQt6.QtCore import Qt, pyqtSignal
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


class Viewport(QOpenGLWidget):
    objectClicked = pyqtSignal(str)   # id hoac ""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene: Scene | None = None
        self.yaw: float = 35.0
        self.pitch: float = 22.0
        self.dist: float = 18.0
        self.target: list[float] = [0.0, 0.0, 0.0]
        self.ortho: bool = False
        self.show_grid: bool = True
        self.show_labels: bool = True

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

    def initializeGL(self) -> None:
        glClearColor(0.11, 0.12, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, max(1, w), max(1, h))

    def _setup_camera(self) -> None:
        w = max(1, self.width())
        h = max(1, self.height())
        aspect = w / h

        if self.ortho:
            s = self.dist * 0.5
            self._proj = ortho_matrix(-s * aspect, s * aspect, -s, s, 0.1, 1000.0)
        else:
            self._proj = perspective_matrix(45.0, aspect, 0.1, 1000.0)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixd(self._proj)

        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = vec3(
            self.target[0] + self.dist * math.cos(pitch) * math.cos(yaw),
            self.target[1] + self.dist * math.cos(pitch) * math.sin(yaw),
            self.target[2] + self.dist * math.sin(pitch),
        )
        self._mv = look_at_matrix(eye, vec3(*self.target), vec3(0.0, 0.0, 1.0))

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixd(self._mv)

        self._vp = (0, 0, w, h)

    # ---------------- paint ----------------
    def paintGL(self) -> None:
        self._reset_gl_state()
        glClearColor(0.11, 0.12, 0.15, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._setup_camera()

        if self.show_grid:
            self._draw_grid()
        self._draw_axes()

        if self.scene is None:
            return
        self._draw_faces()
        self._draw_edges()
        self._draw_points()
        if self.show_labels:
            self._draw_labels()

    def _reset_gl_state(self) -> None:
        """QPainter o frame truoc co the de lai state la; dat lai moi frame."""
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

    def _draw_grid(self) -> None:
        glColor4f(0.25, 0.25, 0.30, 1.0)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for i in range(-10, 11):
            if i == 0:
                continue
            glVertex3f(i, -10, 0); glVertex3f(i, 10, 0)
            glVertex3f(-10, i, 0); glVertex3f(10, i, 0)
        glEnd()

    def _draw_axes(self) -> None:
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.35, 0.35); glVertex3f(0, 0, 0); glVertex3f(7, 0, 0)
        glColor3f(0.4, 1.0, 0.45); glVertex3f(0, 0, 0); glVertex3f(0, 7, 0)
        glColor3f(0.45, 0.6, 1.0); glVertex3f(0, 0, 0); glVertex3f(0, 0, 7)
        glEnd()
        glLineWidth(1.0)

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

        for o in self._visible():
            # Cac khoi da dien da co cac Node 'face' rieng biet voi mau sac tung mat
            if o.kind == "solid":
                continue
            val = o.value
            if isinstance(val, FaceModel):
                self._gl_face_model(val, o.color)
            elif isinstance(val, SolidModel):
                self._gl_face_model(val.face_model, o.color)

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
        """Sinh (p0, p1, color) cho moi canh can ve."""
        for o in self._visible():
            if o.kind == "solid":
                continue
            val = o.value
            if isinstance(val, SegmentData):
                yield val.a, val.b, o.color
            elif isinstance(val, WireFrame):
                c = o.color
                edge_col = (min(1.0, c[0] + 0.25), min(1.0, c[1] + 0.2), min(1.0, c[2]), 0.9)
                for i0, i1 in val.edges:
                    yield val.vertices[i0], val.vertices[i1], edge_col
            elif isinstance(val, SolidModel):
                wf = val.wireframe
                c = o.color
                edge_col = (min(1.0, c[0] + 0.25), min(1.0, c[1] + 0.2), min(1.0, c[2]), 0.9)
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
        glColor4f(0.55, 0.55, 0.62, 0.55)
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

        # 3) Doan noi so do khoang cach
        glLineWidth(1.4)
        glBegin(GL_LINES)
        glColor4f(1.0, 0.9, 0.4, 1.0)
        for o in self._visible(["measure"]):
            if isinstance(o.value, MeasureData) and o.value.segment is not None:
                glVertex3dv(o.value.segment.a)
                glVertex3dv(o.value.segment.b)
        glEnd()

        glDepthFunc(GL_LEQUAL)
        glDepthMask(GL_TRUE)
        glLineWidth(1.0)

    def _draw_points(self) -> None:
        pts = self._visible(["point"])
        glPointSize(9.0)
        glBegin(GL_POINTS)
        for o in pts:
            if o.id == self.selected_id or not isinstance(o.value, np.ndarray):
                continue
            glColor4f(o.color[0], o.color[1], o.color[2], 1.0)
            glVertex3dv(o.value)
        glEnd()

        # Diem dang chon (to hon, mau cam)
        if self.selected_id and self.selected_id in self.scene.objects:
            o = self.scene.objects[self.selected_id]
            if o.visible and o.kind == "point" and isinstance(o.value, np.ndarray):
                glPointSize(14.0)
                glColor3f(1.0, 0.55, 0.1)
                glBegin(GL_POINTS)
                glVertex3dv(o.value)
                glEnd()
        glPointSize(9.0)

    # ---------------- overlay text ----------------
    def _draw_labels(self) -> None:
        if self.scene is None or self._mv is None or self._proj is None:
            return
        p = QPainter(self)
        p.setFont(QFont("Sans", 9))
        for o in self.scene.objects.values():
            if not o.visible or o.value is None:
                continue
            if o.kind == "point" and isinstance(o.value, np.ndarray):
                pt = o.value
                text = o.name
                color = QColor(235, 235, 235)
                off = (7, 3)
            elif o.kind == "measure" and isinstance(o.value, MeasureData):
                pt = o.value.anchor
                text = o.value.text
                color = QColor(255, 225, 120)
                off = (8, -8)
            else:
                continue

            proj = project_to_screen(pt, self._mv, self._proj, self._vp)
            if proj is None:
                continue
            sx, sy, sz = proj
            if sz < 0.0 or sz > 1.0:
                continue
            p.setPen(color)
            p.drawText(int(sx) + off[0], int(sy) + off[1], text)
        p.end()

    # ---------------- mouse & keyboard ----------------
    def mousePressEvent(self, ev) -> None:
        self._last = ev.position()
        if ev.button() == Qt.MouseButton.LeftButton:
            self._mode = "rotate"
            picked = self._try_pick(ev.position())
            self.selected_id = picked or None
            self.objectClicked.emit(picked or "")
            self.update()
        elif ev.button() == Qt.MouseButton.RightButton:
            self._mode = "pan"

    def mouseMoveEvent(self, ev) -> None:
        if self._last is None:
            return
        dx = ev.position().x() - self._last.x()
        dy = ev.position().y() - self._last.y()
        self._last = ev.position()
        if self._mode == "rotate":
            self.yaw -= dx * 0.5
            self.pitch = max(-89.0, min(89.0, self.pitch - dy * 0.5))
            self.update()
        elif self._mode == "pan":
            k = 0.02 * (self.dist / 10.0)
            self.target[0] -= dx * k
            self.target[1] += dy * k
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
        step = self.dist * 0.06
        yaw = math.radians(self.yaw)
        fx, fy = math.cos(yaw), math.sin(yaw)
        rx, ry = -math.sin(yaw), math.cos(yaw)

        if k == Qt.Key.Key_W:
            self.target[0] += fx * step; self.target[1] += fy * step
        elif k == Qt.Key.Key_S:
            self.target[0] -= fx * step; self.target[1] -= fy * step
        elif k == Qt.Key.Key_A:
            self.target[0] -= rx * step; self.target[1] -= ry * step
        elif k == Qt.Key.Key_D:
            self.target[0] += rx * step; self.target[1] += ry * step
        elif k == Qt.Key.Key_Left:
            self.yaw -= 3.0
        elif k == Qt.Key.Key_Right:
            self.yaw += 3.0
        elif k == Qt.Key.Key_Up:
            self.pitch = min(89.0, self.pitch + 3.0)
        elif k == Qt.Key.Key_Down:
            self.pitch = max(-89.0, self.pitch - 3.0)
        elif k == Qt.Key.Key_Home:
            self.reset_view()
        elif k == Qt.Key.Key_5:
            self.ortho = not self.ortho
        elif k == Qt.Key.Key_1:
            self.yaw, self.pitch = 0.0, 0.0
        elif k == Qt.Key.Key_2:
            self.yaw, self.pitch = -90.0, 89.0
        elif k == Qt.Key.Key_3:
            self.yaw, self.pitch = 90.0, 0.0
        elif k == Qt.Key.Key_0:
            self.yaw, self.pitch = 35.0, 22.0
        self.update()

    def reset_view(self) -> None:
        self.yaw, self.pitch, self.dist = 35.0, 22.0, 18.0
        self.target = [0.0, 0.0, 0.0]
        self.ortho = False
        self.update()

    def _try_pick(self, pos) -> str | None:
        if self.scene is None or self._mv is None or self._proj is None:
            return None
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
            d = math.hypot(sx - pos.x(), sy - pos.y())
            if d < bestd:
                bestd, best = d, o.id
        return best