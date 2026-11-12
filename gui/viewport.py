"""OpenGL viewport: camera 360, Oxyz, ve doi tuong, click chon diem."""
import math

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *


class Viewport(QOpenGLWidget):
    objectClicked = pyqtSignal(str)   # id hoac ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = None
        self.yaw = 35.0
        self.pitch = 22.0
        self.dist = 18.0
        self.target = [0.0, 0.0, 0.0]
        self.ortho = False
        self.show_grid = True
        self.show_labels = True
        self._last = None
        self._mode = None
        self._mv = None
        self._proj = None
        self._vp = None
        self.selected_id = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ---------------- setup ----------------
    def set_scene(self, scene):
        self.scene = scene
        self.update()

    def initializeGL(self):
        glClearColor(0.11, 0.12, 0.15, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)

    def resizeGL(self, w, h):
        glViewport(0, 0, max(1, w), max(1, h))

    def _setup_camera(self):
        w = max(1, self.width())
        h = max(1, self.height())
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h
        if self.ortho:
            s = self.dist * 0.5
            glOrtho(-s * aspect, s * aspect, -s, s, 0.1, 1000.0)
        else:
            gluPerspective(45.0, aspect, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = [
            self.target[0] + self.dist * math.cos(pitch) * math.cos(yaw),
            self.target[1] + self.dist * math.cos(pitch) * math.sin(yaw),
            self.target[2] + self.dist * math.sin(pitch),
        ]
        gluLookAt(eye[0], eye[1], eye[2],
                  self.target[0], self.target[1], self.target[2],
                  0, 0, 1)
        self._mv = glGetDoublev(GL_MODELVIEW_MATRIX)
        self._proj = glGetDoublev(GL_PROJECTION_MATRIX)
        self._vp = glGetIntegerv(GL_VIEWPORT)

    # ---------------- paint ----------------
    def paintGL(self):
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

    def _reset_gl_state(self):
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

    def _draw_grid(self):
        glColor4f(0.25, 0.25, 0.30, 1.0)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for i in range(-10, 11):
            if i == 0:
                continue
            glVertex3f(i, -10, 0); glVertex3f(i, 10, 0)
            glVertex3f(-10, i, 0); glVertex3f(10, i, 0)
        glEnd()

    def _draw_axes(self):
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.35, 0.35); glVertex3f(0, 0, 0); glVertex3f(7, 0, 0)
        glColor3f(0.4, 1.0, 0.45); glVertex3f(0, 0, 0); glVertex3f(0, 7, 0)
        glColor3f(0.45, 0.6, 1.0); glVertex3f(0, 0, 0); glVertex3f(0, 0, 7)
        glEnd()
        glLineWidth(1.0)

    def _visible(self, kinds=None):
        if self.scene is None:
            return []
        out = []
        for o in self.scene.objects.values():
            if not o.visible or o.value is None:
                continue
            if kinds and o.kind not in kinds:
                continue
            out.append(o)
        return out

    def _draw_faces(self):
        glDepthMask(GL_TRUE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)
        for o in self._visible():
            if o.kind == "face":
                self._gl_polygon(o.value, o.color)
            elif o.kind == "surface":
                for f in o.value.get("faces", []):
                    self._gl_polygon(f, o.color)
        glDisable(GL_POLYGON_OFFSET_FILL)

    def _gl_polygon(self, pts, color):
        if not pts or len(pts) < 3:
            return
        from core.math3d import normal_of_points
        try:
            n = normal_of_points(pts[0], pts[1], pts[2])
        except Exception:
            n = (0, 0, 1)
        glColor4f(color[0], color[1], color[2],
                  color[3] if len(color) > 3 else 0.35)
        glBegin(GL_POLYGON)
        glNormal3dv(n)
        for p in pts:
            glVertex3dv(p)
        glEnd()

    def _iter_lines(self):
        """Sinh (p0, p1) cho moi canh can ve."""
        for o in self._visible():
            if o.kind in ("segment", "line"):
                a, b = o.value
                yield a, b
            elif o.kind == "surface":
                for poly in o.value.get("polylines", []):
                    for i in range(len(poly) - 1):
                        yield poly[i], poly[i + 1]
                for poly in o.value.get("polylines", []):
                    if len(poly) > 1:
                        yield poly[-1], poly[0]

    def _draw_edges(self):
        lines = list(self._iter_lines())
        # 1) net dut: tat ca canh (ke ca bi che)
        glDepthMask(GL_FALSE)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_LINE_STIPPLE)
        glLineStipple(2, 0xAAAA)
        glLineWidth(1.0)
        glColor4f(0.55, 0.55, 0.62, 0.55)
        glBegin(GL_LINES)
        for a, b in lines:
            glVertex3dv(a); glVertex3dv(b)
        glEnd()
        glDisable(GL_LINE_STIPPLE)
        # 2) net lien: chi canh nhin thay
        glDepthFunc(GL_LESS)
        glLineWidth(1.6)
        glBegin(GL_LINES)
        for o in self._visible():
            if o.kind in ("segment", "line"):
                c = o.color
                glColor4f(c[0], c[1], c[2], 1.0)
                a, b = o.value
                glVertex3dv(a); glVertex3dv(b)
            elif o.kind == "surface":
                c = o.color
                glColor4f(min(1, c[0] + 0.25), min(1, c[1] + 0.2),
                          min(1, c[2]), 0.9)
                for poly in o.value.get("polylines", []):
                    for i in range(len(poly) - 1):
                        glVertex3dv(poly[i]); glVertex3dv(poly[i + 1])
        glEnd()
        # 3) do dac
        glLineWidth(1.4)
        glBegin(GL_LINES)
        glColor4f(1.0, 0.9, 0.4, 1.0)
        for o in self._visible(["measure"]):
            if o.ctor == "distance":
                glVertex3dv(o.value["a"]); glVertex3dv(o.value["b"])
        glEnd()
        glDepthFunc(GL_LEQUAL)
        glDepthMask(GL_TRUE)
        glLineWidth(1.0)

    def _draw_points(self):
        pts = self._visible(["point"])
        # diem thuong
        glPointSize(9.0)
        glBegin(GL_POINTS)
        for o in pts:
            if o.id == self.selected_id:
                continue
            c = o.color
            glColor4f(c[0], c[1], c[2], 1.0)
            glVertex3dv(o.value)
        glEnd()
        # diem dang chon (to hon, mau cam)
        if self.selected_id and self.selected_id in self.scene.objects:
            o = self.scene.objects[self.selected_id]
            if o.visible and o.kind == "point" and o.value is not None:
                glPointSize(14.0)
                glColor3f(1.0, 0.55, 0.1)
                glBegin(GL_POINTS)
                glVertex3dv(o.value)
                glEnd()
        glPointSize(9.0)

    # ---------------- overlay text ----------------
    def _draw_labels(self):
        if self.scene is None:
            return
        p = QPainter(self)
        p.setFont(QFont("Sans", 9))
        for o in self.scene.objects.values():
            if not o.visible:
                continue
            if o.kind == "point":
                pt = o.value
                text = o.name
                color = QColor(235, 235, 235)
                off = (7, 3)
            elif o.kind == "measure":
                v = o.value
                if o.ctor == "distance":
                    pt = (v["a"] + v["b"]) / 2
                else:
                    pt = v["b"]
                text, color, off = v["text"], QColor(255, 225, 120), (8, -8)
            else:
                continue
            if pt is None:
                continue
            try:
                sx, sy, sz = self._project(pt)
            except Exception:
                continue
            if sz < 0 or sz > 1:
                continue
            p.setPen(color)
            p.drawText(int(sx) + off[0], int(sy) + off[1], text)
        p.end()

    def _project(self, p):
        sx, sy, sz = gluProject(float(p[0]), float(p[1]), float(p[2]),
                                self._mv, self._proj, self._vp)
        return (float(sx), float(self._vp[3] - sy), float(sz))

    # ---------------- mouse ----------------
    def mousePressEvent(self, ev):
        self._last = ev.position()
        if ev.button() == Qt.MouseButton.LeftButton:
            self._mode = "rotate"
            picked = self._try_pick(ev.position())
            self.selected_id = picked or None
            self.objectClicked.emit(picked or "")
            self.update()
        elif ev.button() == Qt.MouseButton.RightButton:
            self._mode = "pan"

    def mouseMoveEvent(self, ev):
        if self._last is None:
            return
        dx = ev.position().x() - self._last.x()
        dy = ev.position().y() - self._last.y()
        self._last = ev.position()
        if self._mode == "rotate":
            # keo chuot theo kieu "cam vat the": keo sang phai -> hinh quay sang phai
            self.yaw -= dx * 0.5
            self.pitch = max(-89, min(89, self.pitch - dy * 0.5))
            self.update()
        elif self._mode == "pan":
            k = 0.02 * (self.dist / 10.0)
            self.target[0] -= dx * k
            self.target[1] += dy * k
            self.update()

    def mouseReleaseEvent(self, ev):
        self._last = None
        self._mode = None

    def wheelEvent(self, ev):
        d = ev.angleDelta().y()
        self.dist = max(2.0, min(300.0, self.dist * (0.9 if d > 0 else 1.1)))
        self.update()

    def keyPressEvent(self, ev):
        k = ev.key()
        step = self.dist * 0.06
        yaw = math.radians(self.yaw)
        fx, fy = math.cos(yaw), math.sin(yaw)   # forward (towards view dir on ground)
        rx, ry = -math.sin(yaw), math.cos(yaw)   # right
        if k == Qt.Key.Key_W:
            self.target[0] += fx * step; self.target[1] += fy * step
        elif k == Qt.Key.Key_S:
            self.target[0] -= fx * step; self.target[1] -= fy * step
        elif k == Qt.Key.Key_A:
            self.target[0] -= rx * step; self.target[1] -= ry * step
        elif k == Qt.Key.Key_D:
            self.target[0] += rx * step; self.target[1] += ry * step
        elif k == Qt.Key.Key_Home:
            self.reset_view()
        elif k == Qt.Key.Key_5:
            self.ortho = not self.ortho
        elif k == Qt.Key.Key_1:
            self.yaw, self.pitch = 0, 0
        elif k == Qt.Key.Key_2:
            self.yaw, self.pitch = -90, 89
        elif k == Qt.Key.Key_3:
            self.yaw, self.pitch = 90, 0
        elif k == Qt.Key.Key_0:
            self.yaw, self.pitch = 35, 22
        self.update()

    def reset_view(self):
        self.yaw, self.pitch, self.dist = 35.0, 22.0, 18.0
        self.target = [0.0, 0.0, 0.0]
        self.ortho = False
        self.update()

    def _try_pick(self, pos):
        if self.scene is None or self._mv is None:
            return None
        best, bestd = None, 12.0
        for o in self.scene.objects.values():
            if not o.visible or o.kind != "point" or o.value is None:
                continue
            try:
                sx, sy, sz = self._project(o.value)
            except Exception:
                continue
            if sz < 0 or sz > 1:
                continue
            d = math.hypot(sx - pos.x(), sy - pos.y())
            if d < bestd:
                bestd, best = d, o.id
        return best
