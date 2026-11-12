"""Mo hinh du lieu hinh hoc + do thi phu thuoc (DAG) + undo/redo."""
import json
from contextlib import contextmanager

import numpy as np

from core.math3d import V, normal_of_points, angle_between


class Obj:
    def __init__(self, oid, kind, name, ctor, args=None, color=(0.9, 0.9, 0.9),
                 visible=True, group=""):
        self.id = oid
        self.kind = kind          # point/segment/line/face/solid/surface/measure
        self.name = name
        self.ctor = ctor
        self.args = args or {}
        self.color = tuple(color)
        self.visible = visible
        self.group = group
        self.value = None
        self.error = None

    def to_dict(self):
        return {
            "id": self.id, "kind": self.kind, "name": self.name,
            "ctor": self.ctor, "args": self.args, "color": list(self.color),
            "visible": self.visible, "group": self.group,
        }

    @staticmethod
    def from_dict(d):
        return Obj(d["id"], d["kind"], d["name"], d["ctor"], d.get("args", {}),
                   tuple(d.get("color", [0.9, 0.9, 0.9])),
                   d.get("visible", True), d.get("group", ""))


def _collect_refs(args, scene_objects):
    refs = []

    def walk(x):
        if isinstance(x, str):
            if x in scene_objects:
                refs.append(x)
        elif isinstance(x, (list, tuple)):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            for y in x.values():
                walk(y)

    walk(args)
    return refs


class Scene:
    def __init__(self):
        self.objects = {}        # id -> Obj
        self._counter = 0
        self.listeners = []
        self._history = []
        self._redo = []
        self._in_batch = False

    # ---------- id ----------
    def new_id(self, prefix="o"):
        self._counter += 1
        return f"{prefix}{self._counter}"

    # ---------- history ----------
    def _push(self):
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

    def undo(self):
        if not self._history:
            return False
        self._redo.append(self.to_dict())
        self._restore(self._history.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._history.append(self.to_dict())
        self._restore(self._redo.pop())
        return True

    def _restore(self, d):
        self.objects = {od["id"]: Obj.from_dict(od) for od in d.get("objects", [])}
        self._recompute_counter()
        self.evaluate()
        self._notify(list(self.objects.keys()))

    def _recompute_counter(self):
        mx = 0
        for oid in self.objects:
            num = "".join(ch for ch in oid if ch.isdigit())
            if num:
                mx = max(mx, int(num))
        self._counter = mx

    # ---------- CRUD ----------
    def add(self, obj):
        self._push()
        self.objects[obj.id] = obj
        self._notify([obj.id])
        return obj

    def remove(self, oid):
        """Xoa object + cascade cac object phu thuoc."""
        self._push()
        to_remove = [oid]
        i = 0
        while i < len(to_remove):
            cur = to_remove[i]
            i += 1
            for o in self.objects.values():
                if cur in _collect_refs(o.args, self.objects) and o.id not in to_remove:
                    to_remove.append(o.id)
        removed = []
        for rid in to_remove:
            if rid in self.objects:
                del self.objects[rid]
                removed.append(rid)
        self._notify(removed)
        return removed

    def update(self, oid, history=True, **kw):
        o = self.objects[oid]
        if history:
            self._push()
        for k, v in kw.items():
            setattr(o, k, v)
        self._notify([oid])

    def get(self, oid):
        return self.objects.get(oid)

    # ---------- dependency ----------
    def refs_of(self, oid):
        return _collect_refs(self.objects[oid].args, self.objects)

    def dependents(self, oid):
        return [o.id for o in self.objects.values()
                if oid in _collect_refs(o.args, self.objects)]

    def topo_order(self):
        ids = list(self.objects.keys())
        indeg = {i: 0 for i in ids}
        adj = {i: [] for i in ids}
        for oid in ids:
            for r in self.refs_of(oid):
                if r in indeg:
                    adj[r].append(oid)
                    indeg[oid] += 1
        from collections import deque
        q = deque([i for i in ids if indeg[i] == 0])
        order = []
        while q:
            cur = q.popleft()
            order.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        for i in ids:
            if i not in order:
                order.append(i)          # co chu trinh -> van ve duoc
        return order

    # ---------- evaluate ----------
    def evaluate(self):
        for oid in self.topo_order():
            o = self.objects[oid]
            o.error = None
            try:
                o.value = self._eval(o)
            except Exception as e:
                o.value = None
                o.error = str(e)

    def _eval(self, o):
        c = o.ctor
        g = self.objects
        if c == "fixed":
            return V(*o.args["xyz"])
        if c == "affine":
            acc = np.zeros(3)
            for coef, ref in o.args["terms"]:
                acc = acc + float(coef) * np.asarray(g[ref].value, float)
            return acc
        if c == "on_segment":
            a = np.asarray(g[o.args["a"]].value, float)
            b = np.asarray(g[o.args["b"]].value, float)
            t = float(o.args.get("t", 0.5))
            return a + t * (b - a)
        if c in ("segment", "line"):
            a = np.asarray(g[o.args["a"]].value, float)
            b = np.asarray(g[o.args["b"]].value, float)
            return (a, b)
        if c == "plane":
            pts = [np.asarray(g[p].value, float) for p in o.args["pts"]]
            nrm = normal_of_points(pts[0], pts[1], pts[2])
            d = -float(np.dot(nrm, pts[0]))
            return (pts[0], nrm, d)
        if c == "face":
            return [np.asarray(g[p].value, float) for p in o.args["pts"]]
        if c == "solid":
            return o.args
        if c == "cylinder":
            return _cylinder_value(self, o.args)
        if c == "cone":
            return _cone_value(self, o.args)
        if c == "sphere":
            return _sphere_value(self, o.args)
        if c == "distance":
            a = np.asarray(g[o.args["a"]].value, float)
            b = np.asarray(g[o.args["b"]].value, float)
            d = float(np.linalg.norm(b - a))
            return {"a": a, "b": b, "text": f"{o.name} = {d:.3f}"}
        if c == "angle":
            a = np.asarray(g[o.args["a"]].value, float)
            v = np.asarray(g[o.args["b"]].value, float)
            cpt = np.asarray(g[o.args["c"]].value, float)
            deg = angle_between(a - v, cpt - v)
            return {"a": a, "b": v, "c": cpt, "text": f"{o.name} = {deg:.1f}°"}
        raise ValueError(f"ctor khong ho tro: {c}")

    # ---------- serialize ----------
    def to_dict(self):
        return {"objects": [o.to_dict() for o in self.objects.values()]}

    @classmethod
    def from_dict(cls, d):
        s = cls()
        for od in d.get("objects", []):
            s.objects[od["id"]] = Obj.from_dict(od)
        s._recompute_counter()
        s.evaluate()
        return s

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ---------- notify ----------
    def on_change(self, cb):
        self.listeners.append(cb)

    def _notify(self, ids):
        self.evaluate()
        for cb in self.listeners:
            try:
                cb(ids)
            except Exception:
                pass


# ---------------- mat cong ----------------

def _circle_points(center, r, axis, n):
    center = np.asarray(center, float)
    axis = np.asarray(axis, float)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    # 2 vector truc giao
    tmp = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, tmp); u /= np.linalg.norm(u) + 1e-12
    v = np.cross(axis, u)
    pts = []
    for i in range(n):
        t = 2 * np.pi * i / n
        pts.append(center + r * (np.cos(t) * u + np.sin(t) * v))
    return pts


def _resolve(scene, v):
    if isinstance(v, str):
        return np.asarray(scene.objects[v].value, float)
    return np.asarray(v, float)


def _cylinder_value(scene, args):
    if "bottom" in args:
        bottom = _resolve(scene, args["bottom"])
        top = _resolve(scene, args["top"])
    else:
        bottom = _resolve(scene, args["center"])
        axis = np.asarray(args.get("axis", [0, 0, 1]), float)
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        h = float(args["h"])
        top = bottom + h * axis
    r = float(args["r"])
    axis = top - bottom
    h = float(np.linalg.norm(axis))
    axis = axis / (h + 1e-12)
    n = 32
    bot = _circle_points(bottom, r, axis, n)
    top_pts = _circle_points(top, r, axis, n)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([bot[i], bot[j], top_pts[j], top_pts[i]])
    polylines = [bot + [bot[0]], top_pts + [top_pts[0]]]
    for i in range(0, n, 4):
        polylines.append([bot[i], top_pts[i]])
    return {"faces": faces, "polylines": polylines}


def _cone_value(scene, args):
    if "base" in args:
        base = _resolve(scene, args["base"])
        apex = _resolve(scene, args["apex"])
    else:
        base = _resolve(scene, args["center"])
        axis = np.asarray(args.get("axis", [0, 0, 1]), float)
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        h = float(args["h"])
        apex = base + h * axis
    r = float(args["r"])
    axis = apex - base
    h = float(np.linalg.norm(axis))
    axis = axis / (h + 1e-12)
    n = 32
    base_pts = _circle_points(base, r, axis, n)
    faces = [[base_pts[i], base_pts[(i + 1) % n], apex] for i in range(n)]
    polylines = [base_pts + [base_pts[0]]]
    for i in range(0, n, 8):
        polylines.append([base_pts[i], apex])
    return {"faces": faces, "polylines": polylines}


def _sphere_value(scene, args):
    c = _resolve(scene, args["center"])
    r = float(args["r"])
    n_lat, n_lon = 8, 16
    lines = []
    for i in range(1, n_lat):
        phi = np.pi * i / n_lat
        ring = []
        for j in range(n_lon + 1):
            th = 2 * np.pi * j / n_lon
            ring.append(c + r * np.array([np.sin(phi) * np.cos(th),
                                          np.sin(phi) * np.sin(th),
                                          np.cos(phi)]))
        lines.append(ring)
    for j in range(n_lon):
        th = 2 * np.pi * j / n_lon
        arc = []
        for i in range(n_lat + 1):
            phi = np.pi * i / n_lat
            arc.append(c + r * np.array([np.sin(phi) * np.cos(th),
                                         np.sin(phi) * np.sin(th),
                                         np.cos(phi)]))
        lines.append(arc)
    return {"faces": [], "polylines": lines}
