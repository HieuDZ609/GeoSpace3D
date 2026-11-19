"""Tao thong tin chi tiet (HTML) cho tung doi tuong: diem, doan, mat, khoi, mat cong, so do."""
from __future__ import annotations

import html
import math

import numpy as np

from core.geometry import MeasureData, Node, SegmentData, SolidModel
from core.scene import Scene

KIND_VI = {
    "point": "Điểm", "segment": "Đoạn thẳng", "line": "Đường thẳng", "plane": "Mặt phẳng",
    "face": "Mặt", "solid": "Khối", "surface": "Mặt cong", "wireframe": "Khung dây",
    "curve": "Đường cong", "measure": "Số đo",
}


def fmt(v: float, nd: int = 3) -> str:
    s = f"{float(v):.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def fmt_vec(p) -> str:
    return "(" + ", ".join(fmt(c) for c in p) + ")"


def polygon_normal(verts: np.ndarray) -> np.ndarray:
    """Vector phap tuyen (chua chuan hoa) theo phuong phap Newell; |n| = 2 * dien tich."""
    n = np.zeros(3)
    k = len(verts)
    for i in range(k):
        a, b = verts[i], verts[(i + 1) % k]
        n += np.cross(a, b)
    return n


def polygon_area(verts: np.ndarray) -> float:
    return 0.5 * float(np.linalg.norm(polygon_normal(verts)))


def _row(k: str, v: str) -> str:
    return f"<tr><td style='color:#666;padding-right:10px;'>{k}</td><td><b>{v}</b></td></tr>"


def _table(rows: list[tuple[str, str]]) -> str:
    return "<table cellspacing='2'>" + "".join(_row(k, v) for k, v in rows) + "</table>"


def _h(text: str) -> str:
    return f"<p style='margin:10px 0 2px 0;color:#1a4fa0;'><b>{html.escape(text)}</b></p>"


def _name(scene: Scene, oid: str) -> str:
    o = scene.objects.get(oid)
    return o.name if o else "?"


def _val(scene: Scene, oid: str) -> np.ndarray:
    return np.asarray(scene.objects[oid].value, dtype=np.float64)


def _plane_equation(n: np.ndarray, p0: np.ndarray) -> str:
    nn = np.linalg.norm(n)
    if nn < 1e-12:
        return "(suy biến - các điểm thẳng hàng)"
    n = n / nn
    d = -float(np.dot(n, p0))
    terms = []
    for coef, var in zip(n, "xyz"):
        if abs(coef) < 1e-9:
            continue
        terms.append((coef, var))
    out = ""
    for i, (c, var) in enumerate(terms):
        sign = "-" if c < 0 else "+"
        piece = var if abs(abs(c) - 1) < 1e-9 else f"{fmt(abs(c))}{var}"
        out += f" {sign} {piece}" if i else (f"-{piece}" if c < 0 else piece)
    if abs(d) > 1e-9:
        out += f" {'-' if d < 0 else '+'} {fmt(abs(d))}"
    return out + " = 0"


def _definition(scene: Scene, o: Node) -> str:
    p = o.params
    c = o.ctor
    if c == "fixed":
        return "Điểm cố định (nhập tọa độ)"
    if c == "affine":
        expr = ""
        for coef, ref in p["terms"]:
            coef = float(coef)
            nm = _name(scene, ref)
            sign = "−" if coef < 0 else "+"
            mag = abs(coef)
            term = nm if abs(mag - 1) < 1e-12 else f"{fmt(mag)}·{nm}"
            expr += f" {sign} {term}" if expr else (f"−{term}" if coef < 0 else term)
        return f"Tổ hợp tuyến tính: {o.name} = {expr}"
    if c == "on_segment":
        return (f"Điểm chạy trên đoạn {_name(scene, p['a'])}{_name(scene, p['b'])}, "
                f"t = {fmt(float(p.get('t', 0.5)))}")
    if c in ("segment", "line"):
        return f"Nối {_name(scene, p['a'])} và {_name(scene, p['b'])}"
    if c == "face":
        return "Đa giác qua các điểm " + ", ".join(_name(scene, i) for i in p["pts"])
    if c == "solid":
        return "Khối đa diện tạo từ các mặt"
    return c


def _describe_point(scene: Scene, o: Node) -> str:
    v = np.asarray(o.value, dtype=np.float64)
    rows = [
        ("Tọa độ", fmt_vec(v)),
        ("Cách xác định", html.escape(_definition(scene, o))),
        ("Khoảng cách tới O", fmt(np.linalg.norm(v))),
    ]
    out = _table(rows)

    segs, faces = [], []
    for n in scene.objects.values():
        if n.kind == "segment" and o.id in (n.params.get("a"), n.params.get("b")):
            segs.append(n.name)
        elif n.kind == "face" and o.id in n.params.get("pts", []):
            faces.append(n.name)
    if segs:
        out += _h("Thuộc các đoạn") + html.escape(", ".join(segs))
    if faces:
        out += _h("Thuộc các mặt") + html.escape(", ".join(faces))
    return out


def _describe_segment(scene: Scene, o: Node) -> str:
    sd: SegmentData = o.value
    a, b = sd.a, sd.b
    d = b - a
    L = float(np.linalg.norm(d))
    an, bn = _name(scene, o.params["a"]), _name(scene, o.params["b"])
    rows = [
        (f"Điểm đầu {an}", fmt_vec(a)),
        (f"Điểm cuối {bn}", fmt_vec(b)),
        ("Độ dài", fmt(L)),
        ("Trung điểm", fmt_vec((a + b) / 2)),
        (f"Vector {an}{bn}", fmt_vec(d)),
    ]
    out = _table(rows)
    if L > 1e-12:
        out += _h("Phương trình tham số")
        for c, var, a0, dd in zip("xyz", "xyz", a, d):
            out += f"<br>{var} = {fmt(a0)} {'+' if dd >= 0 else '−'} {fmt(abs(dd))}·t"
        u = d / L
        out += _h("Vector đơn vị") + fmt_vec(u)
    return out


def _face_block(scene: Scene, ids: list[str]) -> str:
    verts = np.array([_val(scene, i) for i in ids])
    names = [_name(scene, i) for i in ids]
    k = len(ids)
    n = polygon_normal(verts)
    area = 0.5 * float(np.linalg.norm(n))
    per = sum(float(np.linalg.norm(verts[(i + 1) % k] - verts[i])) for i in range(k))
    rows = [
        ("Số đỉnh", str(k)),
        ("Diện tích", fmt(area)),
        ("Chu vi", fmt(per)),
    ]
    out = _table(rows)

    out += _h("Phương trình mặt phẳng")
    if np.linalg.norm(n) < 1e-12:
        out += "Các điểm thẳng hàng (mặt suy biến)."
    else:
        un = n / np.linalg.norm(n)
        out += html.escape(_plane_equation(n, verts[0]))
        out += f"<br><span style='color:#666'>Vector pháp tuyến đơn vị:</span> {fmt_vec(un)}"
        dev = max(abs(float(np.dot(un, v - verts[0]))) for v in verts)
        if dev > 1e-6:
            out += (f"<br><span style='color:#c0392b'>Cảnh báo: các điểm không đồng phẳng "
                    f"(lệch tối đa {fmt(dev)}).</span>")

    out += _h("Độ dài các cạnh")
    out += "<br>".join(
        f"{html.escape(names[i] + names[(i + 1) % k])} = {fmt(np.linalg.norm(verts[(i + 1) % k] - verts[i]))}"
        for i in range(k)
    )
    return out


def _describe_face(scene: Scene, o: Node) -> str:
    ids = list(o.params["pts"])
    head = "Đỉnh: " + html.escape(", ".join(_name(scene, i) for i in ids))
    return head + _face_block(scene, ids)


def _describe_solid(scene: Scene, o: Node) -> str:
    sm: SolidModel = o.value
    verts = sm.face_model.vertices
    faces = sm.face_model.faces
    area = sum(polygon_area(verts[f]) for f in faces)
    c = verts.mean(axis=0)
    vol = 0.0
    for f in faces:
        for i in range(1, len(f) - 1):
            vol += abs(float(np.dot(verts[f[0]] - c, np.cross(verts[f[i]] - c, verts[f[i + 1]] - c)))) / 6.0
    rows = [
        ("Số đỉnh", str(len(verts))),
        ("Số cạnh", str(len(sm.wireframe.edges))),
        ("Số mặt", str(len(faces))),
        ("Diện tích toàn phần", fmt(area)),
        ("Thể tích (khối lồi)", fmt(vol)),
    ]
    out = _table(rows)
    out += _h("Các mặt")
    lines = []
    for ids in o.params["faces"]:
        fv = np.array([_val(scene, i) for i in ids])
        lines.append(
            f"{html.escape(''.join(_name(scene, i) for i in ids))}: "
            f"{len(ids)} đỉnh, S = {fmt(polygon_area(fv))}"
        )
    out += "<br>".join(lines)
    return out


def _describe_surface(scene: Scene, o: Node) -> str:
    p = o.params
    c = o.ctor
    r = float(p["r"])
    if c == "cylinder":
        b, t = scene._resolve_vec3(p["bottom"]), scene._resolve_vec3(p["top"])
        h = float(np.linalg.norm(t - b))
        rows = [
            ("Tâm đáy dưới", fmt_vec(b)), ("Tâm đáy trên", fmt_vec(t)),
            ("Bán kính r", fmt(r)), ("Chiều cao h", fmt(h)),
            ("S xung quanh", fmt(2 * math.pi * r * h)),
            ("S toàn phần", fmt(2 * math.pi * r * (r + h))),
            ("Thể tích", fmt(math.pi * r * r * h)),
        ]
    elif c == "cone":
        b, a = scene._resolve_vec3(p["base"]), scene._resolve_vec3(p["apex"])
        h = float(np.linalg.norm(a - b))
        l = math.hypot(r, h)
        rows = [
            ("Tâm đáy", fmt_vec(b)), ("Đỉnh", fmt_vec(a)),
            ("Bán kính r", fmt(r)), ("Chiều cao h", fmt(h)), ("Đường sinh l", fmt(l)),
            ("S xung quanh", fmt(math.pi * r * l)),
            ("S toàn phần", fmt(math.pi * r * (r + l))),
            ("Thể tích", fmt(math.pi * r * r * h / 3)),
        ]
    elif c == "sphere":
        ctr = scene._resolve_vec3(p["center"])
        rows = [
            ("Tâm", fmt_vec(ctr)), ("Bán kính r", fmt(r)),
            ("Diện tích mặt cầu", fmt(4 * math.pi * r * r)),
            ("Thể tích", fmt(4 / 3 * math.pi * r ** 3)),
        ]
    else:
        return ""
    return _table(rows)


def describe(scene: Scene, oid: str | None) -> str:
    """HTML mo ta chi tiet doi tuong `oid`."""
    if not oid or oid not in scene.objects:
        return "<p style='color:#888'>Chọn một điểm, đường, mặt hoặc khối để xem thông tin chi tiết.</p>"
    o = scene.objects[oid]
    head = (f"<p style='font-size:15px;margin:0'><b>{html.escape(o.name)}</b> "
            f"<span style='color:#666'>— {KIND_VI.get(o.kind, o.kind)}</span></p>")
    if o.error:
        return head + f"<p style='color:#c0392b'>Lỗi: {html.escape(o.error)}</p>"
    if o.value is None:
        return head + "<p style='color:#888'>(chưa có dữ liệu)</p>"
    try:
        if o.kind == "point":
            body = _describe_point(scene, o)
        elif o.kind in ("segment", "line"):
            body = _describe_segment(scene, o)
        elif o.kind == "face":
            body = _describe_face(scene, o)
        elif o.kind == "solid":
            body = _describe_solid(scene, o)
        elif o.kind == "surface":
            body = _describe_surface(scene, o)
        elif o.kind == "curve":
            ids = list(o.params.get("pts", []))
            names = [_name(scene, i) for i in ids]
            pts = [np.asarray(scene.objects[i].value, dtype=np.float64) for i in ids if i in scene.objects]
            L = 0.0
            if len(pts) >= 2:
                L = sum(float(np.linalg.norm(pts[j+1]-pts[j])) for j in range(len(pts)-1))
            body = _table([
                ("Số điểm kiểm soát", str(len(ids))),
                ("Điểm kiểm soát", ", ".join(names)),
                ("Số mẫu", str(o.params.get("samples", 60))),
                ("Độ dài xấp xỉ", fmt(L)),
            ])
        elif o.kind == "measure" and isinstance(o.value, MeasureData):
            body = _table([("Giá trị", html.escape(o.value.text))])
        else:
            body = ""
    except Exception as e:  # khong de loi hien thi lam sap giao dien
        body = f"<p style='color:#c0392b'>Không tính được: {html.escape(str(e))}</p>"
    return head + body