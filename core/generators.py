"""Macro sinh Object - khong co ham ve nao.

Moi hinh chi la tap hop Point / Segment / Face / Solid / Surface.
"""
import math

from core.math3d import V
from core.scene import Obj


# ---------------- helpers ----------------

def _uniq_name(scene, name):
    """Tranh trung ten khi them hinh moi vao scene da co san."""
    used = {o.name for o in scene.objects.values()}
    if name not in used:
        return name
    i = 2
    while f"{name}{i}" in used:
        i += 1
    return f"{name}{i}"


def _pt(scene, name, xyz, color=(0.95, 0.95, 0.95)):
    oid = scene.new_id("p")
    scene.add(Obj(oid, "point", _uniq_name(scene, name), "fixed",
                  {"xyz": list(xyz)}, color=color, group="Points"))
    return oid


def _affine(scene, name, terms, color=(0.95, 0.95, 0.95)):
    oid = scene.new_id("p")
    scene.add(Obj(oid, "point", _uniq_name(scene, name), "affine",
                  {"terms": terms}, color=color, group="Points"))
    return oid


def _seg(scene, a, b, color=(0.85, 0.85, 0.95)):
    oid = scene.new_id("s")
    nm = scene.objects[a].name + scene.objects[b].name
    scene.add(Obj(oid, "segment", nm, "segment", {"a": a, "b": b},
                  color=color, group="Segments"))
    return oid


def _face(scene, pts, color=(0.4, 0.6, 0.9, 0.30), name=None):
    oid = scene.new_id("f")
    nm = name or "".join(scene.objects[p].name for p in pts)
    scene.add(Obj(oid, "face", _uniq_name(scene, nm), "face", {"pts": list(pts)},
                  color=color, group="Faces"))
    return oid


def _solid(scene, faces, name):
    oid = scene.new_id("solid")
    scene.add(Obj(oid, "solid", _uniq_name(scene, name), "solid",
                  {"faces": [list(f) for f in faces]},
                  color=(0.5, 0.7, 1.0), group="Solids"))
    return oid


def _wire_box(scene, A, B, C, D, E, F, G, H, col_a, col_b):
    for u, v in [(A, B), (B, C), (C, D), (D, A), (E, F), (F, G), (G, H), (H, E),
                 (A, E), (B, F), (C, G), (D, H)]:
        _seg(scene, u, v)
    fs = [
        _face(scene, [A, B, C, D], col_a, "ABCD"),
        _face(scene, [E, F, G, H], col_a, "EFGH"),
        _face(scene, [A, B, F, E], col_b, "ABFE"),
        _face(scene, [B, C, G, F], col_b, "BCGF"),
        _face(scene, [C, D, H, G], col_b, "CDHG"),
        _face(scene, [D, A, E, H], col_b, "DAEH"),
    ]
    _solid(scene, [[A, B, C, D], [E, F, G, H], [A, B, F, E],
                   [B, C, G, F], [C, D, H, G], [D, A, E, H]], "ABCD.EFGH")
    return fs


# ---------------- khoi da dien ----------------

def gen_cube(scene, A_xyz, edge=2.0):
    e = float(edge)
    ax, ay, az = [float(x) for x in A_xyz]
    with scene.batch():
        A = _pt(scene, "A", (ax, ay, az))
        B = _pt(scene, "B", (ax + e, ay, az))
        D = _pt(scene, "D", (ax, ay + e, az))
        E = _pt(scene, "E", (ax, ay, az + e))
        C = _affine(scene, "C", [[1, B], [-1, A], [1, D]])
        F = _affine(scene, "F", [[1, B], [-1, A], [1, E]])
        G = _affine(scene, "G", [[1, C], [-1, A], [1, E]])
        H = _affine(scene, "H", [[1, D], [-1, A], [1, E]])
        _wire_box(scene, A, B, C, D, E, F, G, H,
                  (0.4, 0.6, 0.9, 0.30), (0.9, 0.5, 0.4, 0.30))
    return {"points": [A, B, C, D, E, F, G, H]}


def gen_box(scene, A_xyz, dx=2.0, dy=2.0, dz=2.0):
    ax, ay, az = [float(x) for x in A_xyz]
    dx, dy, dz = float(dx), float(dy), float(dz)
    with scene.batch():
        A = _pt(scene, "A", (ax, ay, az))
        B = _pt(scene, "B", (ax + dx, ay, az))
        D = _pt(scene, "D", (ax, ay + dy, az))
        E = _pt(scene, "E", (ax, ay, az + dz))
        C = _affine(scene, "C", [[1, B], [-1, A], [1, D]])
        F = _affine(scene, "F", [[1, B], [-1, A], [1, E]])
        G = _affine(scene, "G", [[1, C], [-1, A], [1, E]])
        H = _affine(scene, "H", [[1, D], [-1, A], [1, E]])
        _wire_box(scene, A, B, C, D, E, F, G, H,
                  (0.4, 0.8, 0.6, 0.30), (0.9, 0.7, 0.4, 0.30))
    return {"points": [A, B, C, D, E, F, G, H]}


def gen_pyramid(scene, base_side=4.0, height=5.0):
    a = float(base_side) / 2.0
    h = float(height)
    with scene.batch():
        A = _pt(scene, "A", (-a, -a, 0))
        B = _pt(scene, "B", (a, -a, 0))
        C = _pt(scene, "C", (a, a, 0))
        D = _pt(scene, "D", (-a, a, 0))
        S = _pt(scene, "S", (0, 0, h))
        for u, v in [(A, B), (B, C), (C, D), (D, A),
                     (S, A), (S, B), (S, C), (S, D)]:
            _seg(scene, u, v)
        _face(scene, [A, B, C, D], (0.4, 0.6, 0.9, 0.30), "ABCD")
        _face(scene, [S, A, B], (0.9, 0.5, 0.4, 0.25), "SAB")
        _face(scene, [S, B, C], (0.9, 0.5, 0.4, 0.25), "SBC")
        _face(scene, [S, C, D], (0.9, 0.5, 0.4, 0.25), "SCD")
        _face(scene, [S, D, A], (0.9, 0.5, 0.4, 0.25), "SDA")
        _solid(scene, [[A, B, C, D], [S, A, B], [S, B, C],
                       [S, C, D], [S, D, A]], "S.ABCD")
    return {"points": [A, B, C, D, S]}


def gen_prism(scene, base_side=3.0, height=4.0):
    r = float(base_side)
    h = float(height)
    with scene.batch():
        pts = [(r * math.cos(2 * math.pi * i / 3),
                r * math.sin(2 * math.pi * i / 3), 0.0) for i in range(3)]
        A = _pt(scene, "A", pts[0])
        B = _pt(scene, "B", pts[1])
        C = _pt(scene, "C", pts[2])
        A1 = _pt(scene, "A'", (pts[0][0], pts[0][1], h))
        B1 = _pt(scene, "B'", (pts[1][0], pts[1][1], h))
        C1 = _pt(scene, "C'", (pts[2][0], pts[2][1], h))
        for u, v in [(A, B), (B, C), (C, A), (A1, B1), (B1, C1), (C1, A1),
                     (A, A1), (B, B1), (C, C1)]:
            _seg(scene, u, v)
        _face(scene, [A, B, C], (0.4, 0.6, 0.9, 0.30), "ABC")
        _face(scene, [A1, B1, C1], (0.4, 0.6, 0.9, 0.30), "A'B'C'")
        _face(scene, [A, B, B1, A1], (0.9, 0.7, 0.4, 0.25), "ABB'A'")
        _face(scene, [B, C, C1, B1], (0.9, 0.7, 0.4, 0.25), "BCC'B'")
        _face(scene, [C, A, A1, C1], (0.9, 0.7, 0.4, 0.25), "CAA'C'")
        _solid(scene, [[A, B, C], [A1, B1, C1], [A, B, B1, A1],
                       [B, C, C1, B1], [C, A, A1, C1]], "ABC.A'B'C'")
    return {"points": [A, B, C, A1, B1, C1]}


# ---------------- mat cong ----------------

def _surface(scene, name, ctor, args, color=(0.5, 0.75, 1.0, 0.22)):
    oid = scene.new_id("u")
    scene.add(Obj(oid, "surface", name, ctor, args, color=color, group="Surfaces"))
    return oid


def gen_cylinder(scene, center=(0, 0, 0), r=2.0, h=4.0, axis=(0, 0, 1)):
    with scene.batch():
        O = _pt(scene, "O", center)
        O2 = _pt(scene, "O'", (center[0], center[1], center[2] + h))
        _surface(scene, "Trụ", "cylinder", {"bottom": O, "top": O2, "r": r})
    return O


def gen_cone(scene, center=(0, 0, 0), r=2.0, h=4.0, axis=(0, 0, 1)):
    with scene.batch():
        O = _pt(scene, "O", center)
        S = _pt(scene, "S", (center[0], center[1], center[2] + h))
        _surface(scene, "Nón", "cone", {"base": O, "apex": S, "r": r})
    return S


def gen_sphere(scene, center=(0, 0, 0), r=2.0):
    with scene.batch():
        O = _pt(scene, "O", center)
        _surface(scene, "Cầu", "sphere", {"center": O, "r": r}, color=(0.7, 0.9, 0.9, 0.18))
    return O


# ---------------- diem quan he ----------------

def gen_midpoint(scene, a_id, b_id, name=None):
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    return _affine(scene, name or f"M{an}{bn}",
                   [[0.5, a_id], [0.5, b_id]], (1.0, 0.85, 0.3))


def gen_symmetric(scene, a_id, center_id, name=None):
    an = scene.objects[a_id].name
    return _affine(scene, name or f"{an}'",
                   [[-1, a_id], [2, center_id]], (1.0, 0.7, 0.4))


def gen_divide(scene, a_id, b_id, m, n, name=None):
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    s = float(m + n)
    return _affine(scene, name or f"P{an}{bn}",
                   [[n / s, a_id], [m / s, b_id]], (1.0, 0.85, 0.3))


def gen_on_segment(scene, a_id, b_id, t=0.5, name=None):
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    oid = scene.new_id("p")
    scene.add(Obj(oid, "point", name or f"N{an}{bn}", "on_segment",
                  {"a": a_id, "b": b_id, "t": float(t)},
                  color=(0.4, 1.0, 0.6), group="Points"))
    return oid


# ---------------- do dac ----------------

def gen_distance(scene, a_id, b_id):
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    oid = scene.new_id("m")
    scene.add(Obj(oid, "measure", f"d({an},{bn})", "distance",
                  {"a": a_id, "b": b_id}, color=(1.0, 0.9, 0.4), group="Measures"))
    return oid


def gen_angle(scene, a_id, vertex_id, c_id):
    an = scene.objects[a_id].name
    vn = scene.objects[vertex_id].name
    cn = scene.objects[c_id].name
    oid = scene.new_id("m")
    scene.add(Obj(oid, "measure", f"∠{an}{vn}{cn}", "angle",
                  {"a": a_id, "b": vertex_id, "c": c_id},
                  color=(1.0, 0.9, 0.4), group="Measures"))
    return oid
