"""Phan tich lenh nhap tay (tab "So hoc"), vi du:  A=(1,2,3)   Midpoint(A,B)   Cube(0,0,0,3)."""
from __future__ import annotations

import ast
import math
import operator as op
import re
import string

from core import builders as B
from core.scene import Scene

_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg, ast.UAdd: op.pos,
}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "abs": abs, "radians": math.radians}
_CONSTS = {"pi": math.pi, "e": math.e}


def eval_number(text: str) -> float:
    """Tinh bieu thuc so an toan: 2*sqrt(2), 1/3, pi/2 ..."""
    def ev(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name) and n.id.lower() in _CONSTS:
            return _CONSTS[n.id.lower()]
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id.lower() in _FUNCS and len(n.args) == 1):
            return _FUNCS[n.func.id.lower()](ev(n.args[0]))
        raise ValueError
    try:
        return float(ev(ast.parse(text.strip(), mode="eval")))
    except Exception:
        raise ValueError(f"Không hiểu giá trị số: '{text.strip()}'") from None


def _split_args(s: str) -> list[str]:
    """Tach theo dau phay o muc ngoac 0."""
    out: list[str] = []
    depth, cur = 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def find_point(scene: Scene, name: str) -> str | None:
    for o in scene.objects.values():
        if o.kind == "point" and o.name == name:
            return o.id
    return None


def _pid(scene: Scene, name: str) -> str:
    pid = find_point(scene, name.strip())
    if pid is None:
        raise ValueError(f"Không tìm thấy điểm '{name.strip()}'")
    return pid


def next_point_name(scene: Scene) -> str:
    used = {o.name for o in scene.objects.values()}
    for ch in string.ascii_uppercase:
        if ch not in used:
            return ch
    i = 1
    while f"P{i}" in used:
        i += 1
    return f"P{i}"


def _need(args: list[str], counts: tuple[int, ...], usage: str) -> None:
    if len(args) not in counts:
        raise ValueError(f"Sai cú pháp. Dùng: {usage}")


def _nums(args: list[str]) -> list[float]:
    return [eval_number(a) for a in args]


def _head(args: list[str], n_extra: int) -> tuple[tuple[float, float, float], list[float]]:
    """Cac lenh khoi: co the bo toa do A (mac dinh goc O)."""
    v = _nums(args)
    if len(v) == n_extra:
        return (0.0, 0.0, 0.0), v
    return (v[0], v[1], v[2]), v[3:]


def run_command(scene: Scene, text: str) -> str:
    """Thuc thi 1 lenh. Tra ve thong bao thanh cong; nem ValueError (tieng Viet) neu loi."""
    text = text.strip()
    if not text:
        raise ValueError("Chưa nhập lệnh.")

    name: str | None = None
    m = re.match(r"^([A-Za-z][A-Za-z0-9_']*)\s*=\s*(.+)$", text)
    if m:
        name, text = m.group(1), m.group(2).strip()

    # (x, y, z) -> diem
    if text.startswith("(") and text.endswith(")"):
        args = _split_args(text[1:-1])
        _need(args, (3,), "(x, y, z)")
        nm = name or next_point_name(scene)
        B.gen_point(scene, nm, _nums(args))
        return f"Đã thêm điểm {nm}"

    m = re.match(r"^([A-Za-z_][A-Za-z0-9_']*)\s*\((.*)\)$", text)
    if not m:
        raise ValueError("Không hiểu lệnh. Ví dụ: A=(1,2,3)  hoặc  Midpoint(A,B)")
    fn = m.group(1).lower()
    args = _split_args(m.group(2))

    if fn in ("midpoint", "trungdiem"):
        _need(args, (2,), "Midpoint(A, B)")
        B.gen_midpoint(scene, _pid(scene, args[0]), _pid(scene, args[1]), name=name)
        return "Đã thêm trung điểm"
    if fn in ("segment", "doan", "doanthang"):
        _need(args, (2,), "Segment(A, B)")
        B.gen_segment(scene, _pid(scene, args[0]), _pid(scene, args[1]))
        return f"Đã vẽ đoạn {args[0]}{args[1]}"
    if fn in ("symmetric", "doixung"):
        _need(args, (2,), "Symmetric(A, O)")
        B.gen_symmetric(scene, _pid(scene, args[0]), _pid(scene, args[1]), name=name)
        return "Đã thêm điểm đối xứng"
    if fn in ("divide", "chia"):
        _need(args, (4,), "Divide(A, B, m, n)")
        mm, nn = int(eval_number(args[2])), int(eval_number(args[3]))
        if mm < 1 or nn < 1:
            raise ValueError("m và n phải là số nguyên dương")
        B.gen_divide(scene, _pid(scene, args[0]), _pid(scene, args[1]), mm, nn, name=name)
        return f"Đã chia đoạn theo tỉ lệ {mm}:{nn}"
    if fn in ("onsegment", "diemtrencanh"):
        _need(args, (2, 3), "OnSegment(A, B, t)")
        t = eval_number(args[2]) if len(args) == 3 else 0.5
        B.gen_on_segment(scene, _pid(scene, args[0]), _pid(scene, args[1]), t=t, name=name)
        return "Đã thêm điểm chạy trên đoạn"
    if fn in ("distance", "khoangcach"):
        _need(args, (2,), "Distance(A, B)")
        B.gen_distance(scene, _pid(scene, args[0]), _pid(scene, args[1]))
        return "Đã thêm số đo khoảng cách"
    if fn in ("angle", "goc"):
        _need(args, (3,), "Angle(A, B, C)  (B là đỉnh)")
        B.gen_angle(scene, *[_pid(scene, a) for a in args])
        return "Đã thêm số đo góc"
    if fn in ("face", "mat", "polygon"):
        if len(args) < 3:
            raise ValueError("Mặt cần ít nhất 3 điểm: Face(A, B, C, ...)")
        B.gen_face(scene, [_pid(scene, a) for a in args], name="".join(a.strip() for a in args))
        return "Đã tạo mặt"

    # ----- khoi -----
    if fn in ("cube", "lapphuong"):
        _need(args, (1, 4), "Cube(cạnh)  hoặc  Cube(x, y, z, cạnh)")
        a, (e,) = _head(args, 1)
        B.gen_cube(scene, a, e)
        return "Đã tạo hình lập phương"
    if fn in ("box", "hop", "hophcn"):
        _need(args, (3, 6), "Box(dx, dy, dz)  hoặc  Box(x, y, z, dx, dy, dz)")
        a, (dx, dy, dz) = _head(args, 3)
        B.gen_box(scene, a, dx, dy, dz)
        return "Đã tạo hình hộp chữ nhật"
    if fn in ("pyramid", "chop"):
        _need(args, (2, 5), "Pyramid(cạnh đáy, chiều cao)  hoặc  Pyramid(x, y, z, cạnh đáy, chiều cao)")
        a, (s, h) = _head(args, 2)
        B.gen_pyramid(scene, s, h, center=a)
        return "Đã tạo hình chóp"
    if fn in ("prism", "langtru"):
        _need(args, (2, 5), "Prism(cạnh đáy, chiều cao)  hoặc  Prism(x, y, z, cạnh đáy, chiều cao)")
        a, (s, h) = _head(args, 2)
        B.gen_prism(scene, s, h, center=a)
        return "Đã tạo lăng trụ"
    if fn in ("cylinder", "tru"):
        _need(args, (2, 5), "Cylinder(r, h)  hoặc  Cylinder(x, y, z, r, h)")
        a, (r, h) = _head(args, 2)
        B.gen_cylinder(scene, a, r, h)
        return "Đã tạo hình trụ"
    if fn in ("cone", "non"):
        _need(args, (2, 5), "Cone(r, h)  hoặc  Cone(x, y, z, r, h)")
        a, (r, h) = _head(args, 2)
        B.gen_cone(scene, a, r, h)
        return "Đã tạo hình nón"
    if fn in ("sphere", "cau"):
        _need(args, (1, 4), "Sphere(r)  hoặc  Sphere(x, y, z, r)")
        a, (r,) = _head(args, 1)
        B.gen_sphere(scene, a, r)
        return "Đã tạo hình cầu"

    # Ten(x, y, z) -> diem co ten
    if len(args) == 3:
        try:
            xyz = _nums(args)
        except ValueError:
            xyz = None
        if xyz is not None:
            nm = name or m.group(1)
            B.gen_point(scene, nm, xyz)
            return f"Đã thêm điểm {nm}"
    raise ValueError(f"Lệnh '{m.group(1)}' không được hỗ trợ")


HELP_TEXT = (
    "A=(1,2,3)  hoặc  A(1,2,3)\n"
    "Midpoint(A,B)    Segment(A,B)\n"
    "Divide(A,B,1,2)  Symmetric(A,O)\n"
    "Distance(A,B)    Angle(A,B,C)\n"
    "Face(A,B,C,D)\n"
    "Cube(0,0,0,3)    Box(0,0,0,2,3,4)\n"
    "Pyramid(4,5)     Prism(3,4)\n"
    "Cylinder(2,4)    Cone(2,4)    Sphere(2)\n"
    "(giá trị số: 2*sqrt(2), 1/3, pi ...)"
)