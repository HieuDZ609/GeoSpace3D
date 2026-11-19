from __future__ import annotations

import math
from typing import Sequence
import numpy as np
from core.geometry import Node, RGBA
from core.scene import Scene
from core.math3d import unit

# ---------------- helpers ----------------

def _uniq_name(scene: Scene, name: str) -> str:
    """Tranh trung ten khi them hinh moi vao scene da co san."""
    used = {o.name for o in scene.objects.values()}
    if name not in used:
        return name
    i = 2
    while f"{name}{i}" in used:
        i += 1
    return f"{name}{i}"


def _pt(
    scene: Scene,
    name: str,
    xyz: Sequence[float],
    color: RGBA = (0.12, 0.25, 0.85, 1.0),
) -> str:
    oid = scene.new_id("p")
    scene.add(
        Node(oid, "point", _uniq_name(scene, name), "fixed",
             {"xyz": [float(c) for c in xyz]}, color=color, group="Points")
    )
    return oid


def _affine(
    scene: Scene,
    name: str,
    terms: list[list[float | str]],
    color: RGBA = (0.12, 0.25, 0.85, 1.0),
) -> str:
    oid = scene.new_id("p")
    scene.add(
        Node(oid, "point", _uniq_name(scene, name), "affine",
             {"terms": terms}, color=color, group="Points")
    )
    return oid


def _seg(
    scene: Scene,
    a: str,
    b: str,
    color: RGBA = (0.12, 0.14, 0.22, 1.0),
) -> str:
    oid = scene.new_id("s")
    nm = scene.objects[a].name + scene.objects[b].name
    scene.add(
        Node(oid, "segment", nm, "segment", {"a": a, "b": b},
             color=color, group="Segments")
    )
    return oid


def _face(
    scene: Scene,
    pts: Sequence[str],
    color: RGBA = (0.4, 0.6, 0.9, 0.30),
    name: str | None = None,
) -> str:
    oid = scene.new_id("f")
    nm = name or "".join(scene.objects[p].name for p in pts)
    scene.add(
        Node(oid, "face", _uniq_name(scene, nm), "face", {"pts": list(pts)},
             color=color, group="Faces")
    )
    return oid


def _solid(scene: Scene, faces: list[list[str]], name: str) -> str:
    oid = scene.new_id("solid")
    scene.add(
        Node(oid, "solid", _uniq_name(scene, name), "solid",
             {"faces": [list(f) for f in faces]},
             color=(0.5, 0.7, 1.0, 1.0), group="Solids")
    )
    return oid


def _wire_box(
    scene: Scene,
    A: str, B: str, C: str, D: str,
    E: str, F: str, G: str, H: str,
    col_a: RGBA,
    col_b: RGBA,
) -> None:
    for u, v in [
        (A, B), (B, C), (C, D), (D, A),
        (E, F), (F, G), (G, H), (H, E),
        (A, E), (B, F), (C, G), (D, H),
    ]:
        _seg(scene, u, v)

    faces = [
        [A, B, C, D], [E, F, G, H],
        [A, B, F, E], [B, C, G, F], [C, D, H, G], [D, A, E, H],
    ]
    _face(scene, faces[0], col_a, "ABCD")
    _face(scene, faces[1], col_a, "EFGH")
    _face(scene, faces[2], col_b, "ABFE")
    _face(scene, faces[3], col_b, "BCGF")
    _face(scene, faces[4], col_b, "CDHG")
    _face(scene, faces[5], col_b, "DAEH")
    _solid(scene, faces, "ABCD.EFGH")


# ---------------- doi tuong co ban ----------------

def gen_point(
    scene: Scene,
    name: str,
    xyz: Sequence[float],
    color: RGBA = (0.12, 0.25, 0.85, 1.0),
) -> str:
    return _pt(scene, name, xyz, color=color)


def gen_segment(
    scene: Scene,
    a_id: str,
    b_id: str,
    color: RGBA = (0.12, 0.14, 0.22, 1.0),
) -> str:
    return _seg(scene, a_id, b_id, color=color)


def gen_face(
    scene: Scene,
    pt_ids: Sequence[str],
    color: RGBA = (0.5, 0.7, 1.0, 0.35),
    name: str | None = None,
) -> str:
    return _face(scene, pt_ids, color=color, name=name)


# ---------------- khoi da dien ----------------

def gen_cube(scene: Scene, A_xyz: Sequence[float], edge: float = 2.0) -> dict[str, list[str]]:
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
        _wire_box(
            scene, A, B, C, D, E, F, G, H,
            (0.4, 0.6, 0.9, 0.30), (0.9, 0.5, 0.4, 0.30),
        )
    return {"points": [A, B, C, D, E, F, G, H]}


def gen_box(
    scene: Scene,
    A_xyz: Sequence[float],
    dx: float = 2.0,
    dy: float = 2.0,
    dz: float = 2.0,
) -> dict[str, list[str]]:
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
        _wire_box(
            scene, A, B, C, D, E, F, G, H,
            (0.4, 0.8, 0.6, 0.30), (0.9, 0.7, 0.4, 0.30),
        )
    return {"points": [A, B, C, D, E, F, G, H]}


def gen_pyramid(
    scene: Scene,
    base_side: float = 4.0,
    height: float = 5.0,
) -> dict[str, list[str]]:
    a = float(base_side) / 2.0
    h = float(height)
    with scene.batch():
        A = _pt(scene, "A", (-a, -a, 0.0))
        B = _pt(scene, "B", (a, -a, 0.0))
        C = _pt(scene, "C", (a, a, 0.0))
        D = _pt(scene, "D", (-a, a, 0.0))
        S = _pt(scene, "S", (0.0, 0.0, h))
        for u, v in [
            (A, B), (B, C), (C, D), (D, A),
            (S, A), (S, B), (S, C), (S, D),
        ]:
            _seg(scene, u, v)
        _face(scene, [A, B, C, D], (0.4, 0.6, 0.9, 0.30), "ABCD")
        _face(scene, [S, A, B], (0.9, 0.5, 0.4, 0.25), "SAB")
        _face(scene, [S, B, C], (0.9, 0.5, 0.4, 0.25), "SBC")
        _face(scene, [S, C, D], (0.9, 0.5, 0.4, 0.25), "SCD")
        _face(scene, [S, D, A], (0.9, 0.5, 0.4, 0.25), "SDA")
        _solid(
            scene,
            [[A, B, C, D], [S, A, B], [S, B, C], [S, C, D], [S, D, A]],
            "S.ABCD",
        )
    return {"points": [A, B, C, D, S]}


def gen_prism(
    scene: Scene,
    base_side: float = 3.0,
    height: float = 4.0,
) -> dict[str, list[str]]:
    r = float(base_side)
    h = float(height)
    with scene.batch():
        pts = [
            (r * math.cos(2.0 * math.pi * i / 3.0),
             r * math.sin(2.0 * math.pi * i / 3.0),
             0.0)
            for i in range(3)
        ]
        A = _pt(scene, "A", pts[0])
        B = _pt(scene, "B", pts[1])
        C = _pt(scene, "C", pts[2])
        A1 = _pt(scene, "A'", (pts[0][0], pts[0][1], h))
        B1 = _pt(scene, "B'", (pts[1][0], pts[1][1], h))
        C1 = _pt(scene, "C'", (pts[2][0], pts[2][1], h))
        for u, v in [
            (A, B), (B, C), (C, A),
            (A1, B1), (B1, C1), (C1, A1),
            (A, A1), (B, B1), (C, C1),
        ]:
            _seg(scene, u, v)
        _face(scene, [A, B, C], (0.4, 0.6, 0.9, 0.30), "ABC")
        _face(scene, [A1, B1, C1], (0.4, 0.6, 0.9, 0.30), "A'B'C'")
        _face(scene, [A, B, B1, A1], (0.9, 0.7, 0.4, 0.25), "ABB'A'")
        _face(scene, [B, C, C1, B1], (0.9, 0.7, 0.4, 0.25), "BCC'B'")
        _face(scene, [C, A, A1, C1], (0.9, 0.7, 0.4, 0.25), "CAA'C'")
        _solid(
            scene,
            [[A, B, C], [A1, B1, C1], [A, B, B1, A1], [B, C, C1, B1], [C, A, A1, C1]],
            "ABC.A'B'C'",
        )
    return {"points": [A, B, C, A1, B1, C1]}


# ---------------- mat cong ----------------

def _surface(
    scene: Scene,
    name: str,
    ctor: str,
    params: dict,
    color: RGBA = (0.5, 0.75, 1.0, 0.22),
) -> str:
    oid = scene.new_id("u")
    scene.add(
        Node(oid, "surface", _uniq_name(scene, name), ctor, params,
             color=color, group="Surfaces")
    )
    return oid


def gen_cylinder(
    scene: Scene,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    r: float = 2.0,
    h: float = 4.0,
) -> str:
    with scene.batch():
        O = _pt(scene, "O", center)
        O2 = _pt(scene, "O'", (center[0], center[1], center[2] + float(h)))
        _surface(scene, "Trụ", "cylinder", {"bottom": O, "top": O2, "r": float(r)})
    return O


def gen_cone(
    scene: Scene,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    r: float = 2.0,
    h: float = 4.0,
) -> str:
    with scene.batch():
        O = _pt(scene, "O", center)
        S = _pt(scene, "S", (center[0], center[1], center[2] + float(h)))
        _surface(scene, "Nón", "cone", {"base": O, "apex": S, "r": float(r)})
    return S


def gen_sphere(
    scene: Scene,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    r: float = 2.0,
) -> str:
    with scene.batch():
        O = _pt(scene, "O", center)
        _surface(
            scene, "Cầu", "sphere", {"center": O, "r": float(r)},
            color=(0.7, 0.9, 0.9, 0.18),
        )
    return O


# ---------------- diem quan he ----------------

def gen_midpoint(scene: Scene, a_id: str, b_id: str, name: str | None = None) -> str:
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    return _affine(
        scene,
        name or f"M{an}{bn}",
        [[0.5, a_id], [0.5, b_id]],
        (0.95, 0.50, 0.10, 1.0),
    )


def gen_symmetric(scene: Scene, a_id: str, center_id: str, name: str | None = None) -> str:
    an = scene.objects[a_id].name
    return _affine(
        scene,
        name or f"{an}'",
        [[-1.0, a_id], [2.0, center_id]],
        (0.85, 0.35, 0.10, 1.0),
    )


def gen_divide(
    scene: Scene,
    a_id: str,
    b_id: str,
    m: int,
    n: int,
    name: str | None = None,
) -> str:
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    s = float(m + n)
    return _affine(
        scene,
        name or f"P{an}{bn}",
        [[n / s, a_id], [m / s, b_id]],
        (0.95, 0.50, 0.10, 1.0),
    )


def gen_on_segment(
    scene: Scene,
    a_id: str,
    b_id: str,
    t: float = 0.5,
    name: str | None = None,
) -> str:
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    oid = scene.new_id("p")
    scene.add(
        Node(oid, "point", _uniq_name(scene, name or f"N{an}{bn}"), "on_segment",
             {"a": a_id, "b": b_id, "t": float(t)},
             color=(0.10, 0.65, 0.35, 1.0), group="Points")
    )
    return oid


# ---------------- do dac ----------------

def gen_distance(scene: Scene, a_id: str, b_id: str) -> str:
    an = scene.objects[a_id].name
    bn = scene.objects[b_id].name
    oid = scene.new_id("m")
    scene.add(
        Node(oid, "measure", f"d({an},{bn})", "distance",
             {"a": a_id, "b": b_id},
             color=(0.85, 0.45, 0.00, 1.0), group="Measures")
    )
    return oid


def gen_angle(scene: Scene, a_id: str, vertex_id: str, c_id: str) -> str:
    an = scene.objects[a_id].name
    vn = scene.objects[vertex_id].name
    cn = scene.objects[c_id].name
    oid = scene.new_id("m")
    scene.add(
        Node(oid, "measure", f"∠{an}{vn}{cn}", "angle",
             {"a": a_id, "b": vertex_id, "c": c_id},
             color=(0.85, 0.45, 0.00, 1.0), group="Measures")
    )
    return oid

def gen_altitude_to_plane(
    scene: Scene, point_id: str, plane_pt_ids: list[str], name: str = "H"
) -> tuple[str, str]:
    """Dựng đường cao từ điểm S xuống mặt phẳng qua các điểm (ví dụ MNAB)."""
    # 1. Tạo điểm chân đường cao H phụ thuộc qua Node
    h_id = scene.new_id("p")
    scene.add(
        Node(h_id, "point", _uniq_name(scene, name), "project_to_plane",
             {"point": point_id, "plane_pts": plane_pt_ids},
             color=(0.1, 0.2, 0.9, 1.0), group="Points")
    )
    # 2. Tạo đoạn thẳng SH (hàm _seg tự động ghép tên S + H = SH)
    sh_id = _seg(scene, point_id, h_id, color=(0.1, 0.2, 0.9, 1.0))
    scene.evaluate()
    return h_id, sh_id

def gen_altitude_to_line(
    scene: Scene, point_id: str, a_id: str, b_id: str, name: str = "H"
) -> tuple[str, str]:
    """Dựng đường cao từ điểm S xuống đường thẳng AB."""
    h_id = scene.new_id("p")
    scene.add(
        Node(h_id, "point", _uniq_name(scene, name), "project_to_line",
             {"point": point_id, "a": a_id, "b": b_id},
             color=(0.1, 0.2, 0.9, 1.0), group="Points")
    )
    sh_id = _seg(scene, point_id, h_id, color=(0.1, 0.2, 0.9, 1.0))
    scene.evaluate()
    return h_id, sh_id

def gen_angle_bisector(
    scene: Scene, a_id: str, vertex_id: str, c_id: str, name: str = "D"
) -> tuple[str, str]:
    """Dựng đường phân giác trong của góc B (đỉnh vertex_id)."""
    d_id = scene.new_id("p")
    scene.add(
        Node(d_id, "point", _uniq_name(scene, name), "bisector_point",
             {"a": a_id, "vertex": vertex_id, "c": c_id},
             color=(0.9, 0.5, 0.1, 1.0), group="Points")
    )
    bd_id = _seg(scene, vertex_id, d_id, color=(0.9, 0.5, 0.1, 1.0))
    scene.evaluate()
    return d_id, bd_id

def gen_plane_through_points(scene: Scene, pt_ids: list[str], name: str = "mp") -> str:
    """Tạo một mặt phẳng đa giác đi qua các điểm bất kỳ."""
    face_id = _face(scene, pt_ids, color=(0.5, 0.7, 0.9, 0.45), name=name)
    scene.evaluate()
    return face_id

def gen_perp_bisector_segment(
    scene: Scene, a_id: str, b_id: str, name: str = "M"
) -> str:
    """Dựng mặt phẳng trung trực của đoạn thẳng AB."""
    m_id = gen_midpoint(scene, a_id, b_id, name=name)
    scene.evaluate()
    
    A = np.asarray(scene.objects[a_id].value, dtype=np.float64)
    B = np.asarray(scene.objects[b_id].value, dtype=np.float64)
    n = unit(B - A)
    
    ref = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = unit(np.cross(n, ref))
    v = unit(np.cross(n, u))
    L = 3.0
    M_val = np.asarray(scene.objects[m_id].value, dtype=np.float64)
    
    p1 = _pt(scene, f"K1_{name}", list(M_val + L * u + L * v))
    p2 = _pt(scene, f"K2_{name}", list(M_val - L * u + L * v))
    p3 = _pt(scene, f"K3_{name}", list(M_val - L * u - L * v))
    p4 = _pt(scene, f"K4_{name}", list(M_val + L * u - L * v))
    plane_id = gen_plane_through_points(scene, [p1, p2, p3, p4], name=f"mp_TrungTruc_{name}")
    return plane_id