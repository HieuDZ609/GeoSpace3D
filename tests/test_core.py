import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.builders import (gen_angle, gen_cone, gen_cube, gen_cylinder,
                             gen_distance, gen_midpoint, gen_on_segment,
                             gen_pyramid, gen_sphere, gen_symmetric)
from core.scene import Obj, Scene


def _add(scene, name, xyz):
    oid = scene.new_id("p")
    scene.add(Obj(oid, "point", name, "fixed", {"xyz": list(xyz)}))
    return oid


def test_midpoint():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (4, 0, 0))
    m = gen_midpoint(s, a, b)
    assert np.allclose(s.objects[m].value, [2, 0, 0])


def test_affine_updates_when_parent_moves():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (4, 0, 0))
    m = gen_midpoint(s, a, b)
    s.objects[a].args = {"xyz": [2, 0, 0]}
    s._notify([a])
    assert np.allclose(s.objects[m].value, [3, 0, 0])


def test_cascade_delete():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (4, 0, 0))
    m = gen_midpoint(s, a, b)
    removed = s.remove(a)
    assert a in removed and m in removed
    assert m not in s.objects


def test_cube_derived_vertex():
    s = Scene()
    gen_cube(s, (1, 0, 0), 2.0)
    C = [o for o in s.objects.values() if o.kind == "point" and o.name == "C"][0]
    assert np.allclose(C.value, [3, 2, 0])
    F = [o for o in s.objects.values() if o.kind == "point" and o.name == "F"][0]
    assert np.allclose(F.value, [3, 0, 2])


def test_on_segment():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (10, 0, 0))
    p = gen_on_segment(s, a, b, 0.25)
    assert np.allclose(s.objects[p].value, [2.5, 0, 0])
    s.objects[p].args["t"] = 0.8
    s._notify([p])
    assert np.allclose(s.objects[p].value, [8, 0, 0])


def test_distance_and_angle():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (0, 0, 3))
    v = _add(s, "V", (0, 0, 0))
    c = _add(s, "C", (3, 0, 0))
    d = gen_distance(s, a, b)
    g = gen_angle(s, b, v, c)
    assert "3.000" in s.objects[d].value["text"]
    assert "90.0" in s.objects[g].value["text"]


def test_surfaces():
    s = Scene()
    for oid in (gen_cylinder(s, (0, 0, 0), 2.0, 4.0),
                gen_cone(s, (0, 0, 0), 2.0, 4.0),
                gen_sphere(s, (0, 0, 0), 2.0)):
        assert s.objects[oid].value is not None
    s2 = Scene()
    gen_pyramid(s2, 4.0, 5.0)
    assert all(o.value is not None for o in s2.objects.values())
    u = gen_cylinder(s, (0, 0, 0), 1.0, 2.0)
    surfs = [o for o in s.objects.values() if o.kind == "surface"]
    val = surfs[0].value
    assert len(val["faces"]) == 32
    assert len(val["polylines"][0]) == 33


def test_undo_redo():
    s = Scene()
    a = _add(s, "A", (0, 0, 0))
    b = _add(s, "B", (4, 0, 0))
    m = gen_midpoint(s, a, b)
    n_before = len(s.objects)
    s.remove(m)
    assert len(s.objects) == n_before - 1
    assert s.undo()
    assert m in s.objects
    assert s.redo()
    assert m not in s.objects


def test_serialize_roundtrip():
    s = Scene()
    gen_cube(s, (0, 0, 0), 2.0)
    gen_cylinder(s, (0, 0, 0), 1.0, 3.0)
    path = "/tmp/opencode/test_roundtrip.json"
    os.makedirs("/tmp/opencode", exist_ok=True)
    s.save(path)
    s2 = Scene.load(path)
    assert len(s2.objects) == len(s.objects)
    C1 = [o for o in s.objects.values() if o.kind == "point" and o.name == "C"][0]
    C2 = [o for o in s2.objects.values() if o.kind == "point" and o.name == "C"][0]
    assert np.allclose(C1.value, C2.value)


def test_symmetric():
    s = Scene()
    a = _add(s, "A", (2, 0, 0))
    o = _add(s, "O", (0, 0, 0))
    ap = gen_symmetric(s, a, o)
    assert np.allclose(s.objects[ap].value, [-2, 0, 0])


def test_delete_cascade_removes_faces():
    s = Scene()
    gen_pyramid(s, 4.0, 5.0)
    S = [o for o in s.objects.values() if o.kind == "point" and o.name == "S"][0]
    removed = s.remove(S.id)
    # 4 canh ben + 4 mat ben + solid
    assert len(removed) >= 9
