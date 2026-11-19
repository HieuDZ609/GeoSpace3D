"""Mo hinh du lieu hinh hoc + do thi phu thuoc (DAG) + undo/redo."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import json
from typing import Any, Callable

import numpy as np

from core.geometry import (
    FaceModel,
    GeomValue,
    MeasureData,
    Node,
    PlaneData,
    SegmentData,
    SolidModel,
    WireFrame,
)
from core.math3d import (angle_between, normal_of_points, unit, vec3,
                         project_point_to_plane, project_point_to_line,
                         angle_bisector_point, safe_eval_expr)
from core.primitives import build_cone, build_cylinder, build_sphere


def _collect_refs(params: Any, scene_objects: dict[str, Node]) -> list[str]:
    """Quet de quy tat ca ID doi tuong duoc tham chieu trong params."""
    refs: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            if x in scene_objects:
                refs.append(x)
        elif isinstance(x, (list, tuple)):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            for y in x.values():
                walk(y)

    walk(params)
    return refs


class Scene:
    def __init__(self) -> None:
        self.objects: dict[str, Node] = {}
        self._counter: int = 0
        self.listeners: list[Callable[[list[str]], None]] = []
        self._history: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._in_batch: bool = False

    # ---------- ID ----------
    def new_id(self, prefix: str = "o") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    # ---------- History (Undo / Redo) ----------
    def _push(self) -> None:
        if self._in_batch:
            return
        self._history.append(self.to_dict())
        self._history = self._history[-60:]
        self._redo.clear()

    @contextmanager
    def batch(self):
        """Gom nhieu thay doi thanh 1 buoc undo."""
        self._push()
        self._in_batch = True
        try:
            yield self
        finally:
            self._in_batch = False
            self._notify(list(self.objects.keys()))

    def undo(self) -> bool:
        if not self._history:
            return False
        self._redo.append(self.to_dict())
        self._restore(self._history.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._history.append(self.to_dict())
        self._restore(self._redo.pop())
        return True

    def _restore(self, data: dict[str, Any]) -> None:
        self.objects = {
            od["id"]: Node.from_dict(od) for od in data.get("objects", [])
        }
        self._recompute_counter()
        self.evaluate()
        self._notify(list(self.objects.keys()))

    def _recompute_counter(self) -> None:
        mx = 0
        for oid in self.objects:
            num = "".join(ch for ch in oid if ch.isdigit())
            if num:
                mx = max(mx, int(num))
        self._counter = mx

    # ---------- CRUD ----------
    def add(self, node: Node) -> Node:
        self._push()
        self.objects[node.id] = node
        self._notify([node.id])
        return node

    def remove(self, oid: str) -> list[str]:
        """Xoa object + xoa day chuyen cac object con phu thuoc."""
        self._push()
        to_remove = [oid]
        i = 0
        while i < len(to_remove):
            cur = to_remove[i]
            i += 1
            for o in self.objects.values():
                if cur in _collect_refs(o.params, self.objects) and o.id not in to_remove:
                    to_remove.append(o.id)
        removed: list[str] = []
        for rid in to_remove:
            if rid in self.objects:
                del self.objects[rid]
                removed.append(rid)
        self._notify(removed)
        return removed

    def update(self, oid: str, history: bool = True, **kw: Any) -> None:
        node = self.objects[oid]
        if history:
            self._push()
        for k, v in kw.items():
            setattr(node, k, v)
        self._notify([oid])

    def get(self, oid: str) -> Node | None:
        return self.objects.get(oid)

    # ---------- Dependency Graph (DAG) ----------
    def refs_of(self, oid: str) -> list[str]:
        return _collect_refs(self.objects[oid].params, self.objects)

    def dependents(self, oid: str) -> list[str]:
        return [
            o.id for o in self.objects.values()
            if oid in _collect_refs(o.params, self.objects)
        ]

    def topo_order(self) -> list[str]:
        ids = list(self.objects.keys())
        indeg = {i: 0 for i in ids}
        adj: dict[str, list[str]] = {i: [] for i in ids}
        for oid in ids:
            for r in self.refs_of(oid):
                if r in indeg:
                    adj[r].append(oid)
                    indeg[oid] += 1
        q = deque([i for i in ids if indeg[i] == 0])
        order: list[str] = []
        while q:
            cur = q.popleft()
            order.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        for i in ids:
            if i not in order:
                order.append(i)
        return order

    # ---------- Evaluate ----------
    def evaluate(self) -> None:
        for oid in self.topo_order():
            node = self.objects[oid]
            node.error = None
            try:
                node.value = self._eval(node)
            except Exception as e:
                node.value = None
                node.error = str(e)

    def _resolve_vec3(self, v: Any) -> np.ndarray:
        if isinstance(v, str):
            val = self.objects[v].value
            if not isinstance(val, np.ndarray):
                raise ValueError(f"Doi tuong '{v}' khong phai toa do diem")
            return val
        return np.asarray(v, dtype=np.float64)

    def _eval(self, node: Node) -> GeomValue:
        c = node.ctor
        p = node.params
        g = self.objects

        if c == "fixed":
            return vec3(*p["xyz"])

        if c == "affine":
            acc = np.zeros(3, dtype=np.float64)
            for coef, ref in p["terms"]:
                acc = acc + float(coef) * np.asarray(g[ref].value, dtype=np.float64)
            return acc

        if c == "on_segment":
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            b = np.asarray(g[p["b"]].value, dtype=np.float64)
            t = float(p.get("t", 0.5))
            return a + t * (b - a)

        if c in ("segment", "line"):
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            b = np.asarray(g[p["b"]].value, dtype=np.float64)
            return SegmentData(a=a, b=b)

        if c == "plane":
            pts = [np.asarray(g[pid].value, dtype=np.float64) for pid in p["pts"]]
            nrm = normal_of_points(pts[0], pts[1], pts[2])
            d = -float(np.dot(nrm, pts[0]))
            return PlaneData(origin=pts[0], normal=nrm, d=d)

        if c == "face":
            pts = [np.asarray(g[pid].value, dtype=np.float64) for pid in p["pts"]]
            verts = np.array(pts, dtype=np.float64)
            return FaceModel(vertices=verts, faces=[list(range(len(pts)))])

        if c == "solid":
            faces_ids: list[list[str]] = p["faces"]
            pt_ids: list[str] = []
            idx_map: dict[str, int] = {}
            for face_loop in faces_ids:
                for pid in face_loop:
                    if pid not in idx_map:
                        idx_map[pid] = len(pt_ids)
                        pt_ids.append(pid)
            verts = np.array([g[pid].value for pid in pt_ids], dtype=np.float64)
            faces = [[idx_map[pid] for pid in f] for f in faces_ids]
            edge_set: set[tuple[int, int]] = set()
            for f in faces:
                for i in range(len(f)):
                    u, v = f[i], f[(i + 1) % len(f)]
                    edge_set.add((min(u, v), max(u, v)))
            return SolidModel(
                face_model=FaceModel(vertices=verts, faces=faces),
                wireframe=WireFrame(vertices=verts, edges=sorted(edge_set)),
            )

        if c == "cylinder":
            if "bottom" in p:
                bottom = self._resolve_vec3(p["bottom"])
                top = self._resolve_vec3(p["top"])
            else:
                bottom = self._resolve_vec3(p["center"])
                ax = unit(np.asarray(p.get("axis", [0.0, 0.0, 1.0]), dtype=np.float64))
                top = bottom + float(p["h"]) * ax
            return build_cylinder(bottom, top, float(p["r"]))

        if c == "cone":
            if "base" in p:
                base = self._resolve_vec3(p["base"])
                apex = self._resolve_vec3(p["apex"])
            else:
                base = self._resolve_vec3(p["center"])
                ax = unit(np.asarray(p.get("axis", [0.0, 0.0, 1.0]), dtype=np.float64))
                apex = base + float(p["h"]) * ax
            return build_cone(base, apex, float(p["r"]))

        if c == "sphere":
            center = self._resolve_vec3(p["center"])
            return build_sphere(center, float(p["r"]))

        if c == "distance":
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            b = np.asarray(g[p["b"]].value, dtype=np.float64)
            d = float(np.linalg.norm(b - a))
            return MeasureData(
                anchor=(a + b) * 0.5,
                text=f"{node.name} = {d:.3f}",
                segment=SegmentData(a=a, b=b),
            )

        if c == "angle":
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            v = np.asarray(g[p["b"]].value, dtype=np.float64)
            cpt = np.asarray(g[p["c"]].value, dtype=np.float64)
            deg = angle_between(a - v, cpt - v)
            return MeasureData(
                anchor=v,
                text=f"{node.name} = {deg:.1f}°",
                segment=None,
            )

         # 1. Chân đường cao hạ xuống mặt phẳng
        if c == "project_to_plane":
            s = np.asarray(g[p["point"]].value, dtype=np.float64)
            # Lấy toạ độ các điểm của mặt phẳng
            pts = [np.asarray(g[pid].value, dtype=np.float64) for pid in p["plane_pts"]]
            nrm = normal_of_points(pts[0], pts[1], pts[2])
            return project_point_to_plane(s, pts[0], nrm)
        
        # 2. Chân đường cao hạ xuống đường thẳng / đoạn thẳng
        if c == "project_to_line":
            s = np.asarray(g[p["point"]].value, dtype=np.float64)
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            b = np.asarray(g[p["b"]].value, dtype=np.float64)
            return project_point_to_line(s, a, b)
        
        # 3. Chân đường phân giác trong
        if c == "bisector_point":
            a = np.asarray(g[p["a"]].value, dtype=np.float64)
            v = np.asarray(g[p["vertex"]].value, dtype=np.float64)
            c_pt = np.asarray(g[p["c"]].value, dtype=np.float64)
            return angle_bisector_point(a, v, c_pt)
        
        if c == "bezier":
            pts_ids: list[str] = p["pts"]
            ctrl = [np.asarray(g[pid].value, dtype=np.float64) for pid in pts_ids]
            if len(ctrl) < 2:
                raise ValueError("Bezier can it nhat 2 diem kiem soat")
            n = len(ctrl) - 1
            m = int(p.get("samples", 60))
            if m < 2:
                m = 2
            from math import comb
            verts: list[np.ndarray] = []
            for i in range(m + 1):
                t = i / m
                pt = np.zeros(3, dtype=np.float64)
                for k in range(n + 1):
                    pt += comb(n, k) * ((1.0 - t) ** (n - k)) * (t ** k) * ctrl[k]
                verts.append(pt)
            arr = np.array(verts, dtype=np.float64)
            edges = [(i, i + 1) for i in range(len(verts) - 1)]
            return WireFrame(vertices=arr, edges=edges)

        if c == "parametric":
            Xe, Ye, Ze = p["X"], p["Y"], p["Z"]
            umin = float(p["umin"]); umax = float(p["umax"])
            vmin = float(p["vmin"]); vmax = float(p["vmax"])
            nu = int(p["nu"]); nv = int(p["nv"])
            if nu < 1:
                nu = 1
            if nv < 1:
                nv = 1
            coeffs = p.get("coeffs", {}) or {}
            verts: list[list[float]] = []
            grid: list[list[int]] = []
            for i in range(nu + 1):
                u = umin + (umax - umin) * i / nu
                row: list[int] = []
                for j in range(nv + 1):
                    v = vmin + (vmax - vmin) * j / nv
                    ctx = {"u": u, "v": v}
                    ctx.update(coeffs)
                    x = safe_eval_expr(Xe, ctx)
                    y = safe_eval_expr(Ye, ctx)
                    z = safe_eval_expr(Ze, ctx)
                    row.append(len(verts))
                    verts.append([x, y, z])
                grid.append(row)
            arr = np.array(verts, dtype=np.float64)
            faces: list[list[int]] = []
            edge_set: set[tuple[int, int]] = set()
            for i in range(nu):
                for j in range(nv):
                    a = grid[i][j]
                    b = grid[i + 1][j]
                    cc = grid[i + 1][j + 1]
                    d = grid[i][j + 1]
                    faces.append([a, b, cc, d])
                    for u_, v_ in ((a, b), (b, cc), (cc, d), (d, a)):
                        edge_set.add((min(u_, v_), max(u_, v_)))
            return SolidModel(
                face_model=FaceModel(vertices=arr, faces=faces),
                wireframe=WireFrame(vertices=arr, edges=sorted(edge_set)),
            )

        raise ValueError(f"ctor khong ho tro: {c}")

    # ---------- Serialize (JSON) ----------
    def to_dict(self) -> dict[str, Any]:
        return {"objects": [o.to_dict() for o in self.objects.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        s = cls()
        for od in data.get("objects", []):
            s.objects[od["id"]] = Node.from_dict(od)
        s._recompute_counter()
        s.evaluate()
        return s

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> Scene:
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ---------- Observer ----------
    def on_change(self, cb: Callable[[list[str]], None]) -> None:
        self.listeners.append(cb)

    def _notify(self, ids: list[str]) -> None:
        self.evaluate()
        for cb in self.listeners:
            try:
                cb(ids)
            except Exception:
                pass