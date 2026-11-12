"""Toan hoc 3D thuan numpy - khong phu thuoc Qt/OpenGL."""
import numpy as np


def V(x=0.0, y=0.0, z=0.0):
    return np.array([float(x), float(y), float(z)], dtype=float)


def add(a, b): return np.asarray(a, float) + np.asarray(b, float)
def sub(a, b): return np.asarray(a, float) - np.asarray(b, float)
def scale(s, a): return float(s) * np.asarray(a, float)
def dot(a, b): return float(np.dot(a, b))
def cross(a, b): return np.cross(a, b)
def norm(a): return float(np.linalg.norm(a))
def unit(a):
    n = norm(a)
    return np.asarray(a, float) / n if n > 1e-12 else np.zeros(3)


def normal_of_points(p0, p1, p2):
    return unit(cross(sub(p1, p0), sub(p2, p0)))


def project_point_to_screen(p, modelview, projection, viewport):
    """Tra ve (sx, sy, depth) hoac None neu nam sau camera."""
    import OpenGL.GLU as glu
    sx, sy, sz = glu.gluProject(float(p[0]), float(p[1]), float(p[2]),
                                modelview, projection, viewport)
    # gluProject tra y tinh tu duoi len; chuyen sang y tu tren xuong
    h = viewport[3]
    return (float(sx), float(h - sy), float(sz))


def angle_between(u, v):
    """Goc (do) giua 2 vector."""
    import math
    u = np.asarray(u, float); v = np.asarray(v, float)
    nu = np.linalg.norm(u); nv = np.linalg.norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    c = float(np.dot(u, v) / (nu * nv))
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def plane_from_points(p0, p1, p2):
    n = normal_of_points(p0, p1, p2)
    d = -dot(n, p0)
    return n, d


def point_on_plane(p, n, d, eps=1e-9):
    return abs(dot(n, p) + d) < eps