from __future__ import annotations

import numpy as np

from core.geometry import FaceModel, SolidModel, WireFrame
from core.math3d import Vec3, unit

#tạo vòng tròn nằm trong 3D
def _circle_ring(center: Vec3, r: float, axis: Vec3, n: int) -> np.ndarray:
    ax = unit(axis)
    ref = np.array([1.0, 0.0, 0.0]) if abs(ax[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = unit(np.cross(ax, ref))
    v = np.cross(ax, u)
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return center + r * (np.outer(np.cos(angles), u) + np.outer(np.sin(angles), v))


#tạo hình trụ
def build_cylinder(bottom: Vec3, top: Vec3, r: float, segments: int = 32) -> SolidModel:
    axis = top - bottom
    bot_ring = _circle_ring(bottom, r, axis, segments)
    top_ring = _circle_ring(top, r, axis, segments)
    # 0 .. segments-1: day duoi | segments .. 2*segments-1: day tren
    vertices = np.vstack([bot_ring, top_ring])

    edges: list[tuple[int, int]] = []
    faces: list[list[int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        edges.append((i, j))                        # canh day duoi
        edges.append((segments + i, segments + j))  # canh day tren
        if i % 4 == 0:
            edges.append((i, segments + i))         # duong sinh
        faces.append([i, j, segments + j, segments + i])

    return SolidModel(
        face_model=FaceModel(vertices=vertices, faces=faces),
        wireframe=WireFrame(vertices=vertices, edges=edges),
    )

#tạo hình nón
def build_cone(base: Vec3, apex: Vec3, r: float, segments: int = 32) -> SolidModel:
    ring = _circle_ring(base, r, apex - base, segments)
    # 0 .. segments-1: duong tron day | segments: dinh non S
    vertices = np.vstack([ring, apex.reshape(1, 3)])
    apex_idx = segments

    edges: list[tuple[int, int]] = []
    faces: list[list[int]] = []
    for i in range(segments):
        j = (i + 1) % segments
        edges.append((i, j))
        if i % 8 == 0:
            edges.append((i, apex_idx))
        faces.append([i, j, apex_idx])

    return SolidModel(
        face_model=FaceModel(vertices=vertices, faces=faces),
        wireframe=WireFrame(vertices=vertices, edges=edges),
    )

#Tạo khung dây hình cầu
def build_sphere(center: Vec3, r: float, n_lat: int = 8, n_lon: int = 16) -> WireFrame:
    verts: list[np.ndarray] = [center + np.array([0.0, 0.0, r])]  # index 0: cuc Bac

    for i in range(1, n_lat):
        phi = np.pi * i / n_lat
        sin_p, cos_p = np.sin(phi), np.cos(phi)
        for j in range(n_lon):
            th = 2.0 * np.pi * j / n_lon
            offset = r * np.array([sin_p * np.cos(th), sin_p * np.sin(th), cos_p])
            verts.append(center + offset)

    south_idx = len(verts)
    verts.append(center + np.array([0.0, 0.0, -r]))               # cuc Nam
    vertices = np.array(verts, dtype=np.float64)

    def ring_idx(lat_i: int, lon_j: int) -> int:
        return 1 + (lat_i - 1) * n_lon + (lon_j % n_lon)

    edges: list[tuple[int, int]] = []
    # Cac vong vi tuyen
    for i in range(1, n_lat):
        for j in range(n_lon):
            edges.append((ring_idx(i, j), ring_idx(i, j + 1)))

    # Cac cung kinh tuyen tu cuc Bac xuong cuc Nam
    for j in range(n_lon):
        edges.append((0, ring_idx(1, j)))
        for i in range(1, n_lat - 1):
            edges.append((ring_idx(i, j), ring_idx(i + 1, j)))
        edges.append((ring_idx(n_lat - 1, j), south_idx))

    return WireFrame(vertices=vertices, edges=edges)