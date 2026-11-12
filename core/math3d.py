from __future__ import annotations

import math
import numpy as np

Vec3 = np.ndarray  
Mat4 = np.ndarray

def vec3(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Vec3:
    return np.array([float(x), float(y), float(z)], dtype=np.float64)

#Phép cộng 2 vector
def add(a: Vec3, b: Vec3) -> Vec3:
    return np.asarray(a, dtype=np.float64) + np.asarray(b, dtype=np.float64)

#Phép trừ 2 vector
def sub(a: Vec3, b: Vec3) -> Vec3:
    return np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
#Phép tỉ lệ số thực * vector
def scale(s: float, a: Vec3) -> Vec3:
    return float(s) * np.asarray(a, dtype=np.float64)
#Tích vô hướng của 2 vector (là 1 giá trị)
def dot(a: Vec3, b: Vec3) -> float:
    return float(np.dot(a, b))
#Tích có hướng của 2 vector (là 1 vector)
def cross(a: Vec3, b: Vec3) -> Vec3:
    return np.cross(a, b)
# Độ dài vector
def norm(a: Vec3) -> float:
    return float(np.linalg.norm(a))
# Chuẩn hóa vector (lấy vector / độ dài của nó)
def unit(a: Vec3) -> Vec3:
    v = np.asarray(a, dtype=np.float64)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.zeros(3, dtype=np.float64)

#Xác định vector pháp tuyến của 3 điểm po,p1,p2
   # Xác định mặt của tam giác dựa vào hướng vector pháp tuyến
def normal_of_points(p0: Vec3, p1: Vec3, p2: Vec3) -> Vec3:
    return unit(np.cross(sub(p1, p0), sub(p2, p0)))

#Tính góc của 2 vector
def angle_between(u: Vec3, v: Vec3) -> float:
    nu, nv = norm(u), norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    cos_a = max(-1.0, min(1.0, dot(u, v) / (nu * nv)))
    return math.degrees(math.acos(cos_a))
#Phương trình mặt phẳng từ 3 điểm (2 vector)
#Ax+By+Cz+D=0 (D=-(Ax0+By0+Cz0))
def plane_from_points(p0: Vec3, p1: Vec3, p2: Vec3) -> tuple[Vec3, float]:
    n = normal_of_points(p0, p1, p2)
    d = -dot(n, p0)
    return n, d
#Điểm trên mặt phẳng
def point_on_plane(p: Vec3, n: Vec3, d: float, eps: float = 1e-9) -> bool:
    return abs(dot(n, p) + d) < eps



### Ma trận biến đổi 
#Ma trận cấp 4
def mat4_identity() -> Mat4:
    return np.eye(4, dtype=np.float64)

# Nhân 2 ma trận
def multiply_matrix(A: Mat4, B: Mat4) -> Mat4:
    return A @ B

# Phép biến đổi
#Ma trận tịnh tiến
def translate(tx: float, ty: float, tz: float) -> Mat4:
    M = mat4_identity()
    M[3, 0] = float(tx)
    M[3, 1] = float(ty)
    M[3, 2] = float(tz)
    return M

#Ma trận đối xứng xy
def reflect_xy() -> Mat4:
    M = mat4_identity()
    M[2, 2] = -1.0
    return M

#Ma trận đối xứng xz
def reflect_xz() -> Mat4:
    M = mat4_identity()
    M[1, 1] = -1.0
    return M

#Ma trận đối xứng yz
def reflect_yz() -> Mat4:
    M = mat4_identity()
    M[0, 0] = -1.0
    return M

#Đối xứng qua gốc tọa độ
def reflect_o() -> Mat4:
    M = mat4_identity()
    M[0, 0] = -1.0
    M[1, 1] = -1.0
    M[2, 2] = -1.0
    return M

#Ma trận tỉ lệ gốc tọa độ
def scaling_o(sx: float, sy: float, sz: float) -> Mat4:
    M = mat4_identity()
    M[0, 0] = float(sx)
    M[1, 1] = float(sy)
    M[2, 2] = float(sz)
    return M

#Ma trận tỉ lệ tại điểm khác O
# tịnh tiến về o , scale, rồi tịnh tiến ra lại
def scaling_with_point(
    sx: float, sy: float, sz: float,
    x: float, y: float, z: float,
) -> Mat4:
    M = mat4_identity()
    M1 = translate(-x, -y, -z)
    M2 = scaling_o(sx, sy, sz)
    M3 = translate(x, y, z)

    M = multiply_matrix(M1,M2)
    M = multiply_matrix(M, M3)
    return M

#Ma trận quay trục x
def rotate_x(angle_deg: float) -> Mat4:
    M = mat4_identity()
    a = math.radians(angle_deg)
    M[1, 1] = math.cos(a)
    M[1, 2] = math.sin(a)
    M[2, 1] = -math.sin(a)
    M[2, 2] = math.cos(a)
    return M

#Ma trận quay trục y
def rotate_y(angle_deg: float) -> Mat4:
    M = mat4_identity()
    a = math.radians(angle_deg)
    M[0, 0] = math.cos(a)
    M[0, 2] = -math.sin(a)
    M[2, 0] = math.sin(a)
    M[2, 2] = math.cos(a)
    return M

#Ma trận quay trục z
def rotate_z(angle_deg: float) -> Mat4:
    M = mat4_identity()
    a = math.radians(angle_deg)
    M[0, 0] = math.cos(a)
    M[0, 1] = math.sin(a)
    M[1, 0] = -math.sin(a)
    M[1, 1] = math.cos(a)
    return M

#Ma tran quay quanh truc bat ky
#tinh tien k ve goc toa do, quay quanh truc x dua len mp Oxz
#Quay quanh y de dua trung truc Oz
#Thực hiện ngược lại
def rotate_around_axis(
    angle_deg: float,
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
) -> Mat4:
    dx, dy, dz = float(x2 - x1), float(y2 - y1), float(z2 - z1)
    T1 = translate(-x1, -y1, -z1)

    d = math.hypot(dy, dz)
    alpha_x = math.degrees(math.acos(max(-1.0, min(1.0, dz / d)))) if d > 1e-12 else 0.0
    RX = rotate_x(alpha_x)

    l = math.hypot(d, dx)
    alpha_z = math.degrees(math.acos(max(-1.0, min(1.0, d / l)))) if l > 1e-12 else 0.0
    RY = rotate_y(-alpha_z)

    RZ = rotate_z(angle_deg)
    RY2 = rotate_y(alpha_z)
    RX2 = rotate_x(-alpha_x)
    T2 = translate(x1, y1, z1)

    return T1 @ RX @ RY @ RZ @ RY2 @ RX2 @ T2

# Điểm P' sau khi P1 được biến đổi bởi M 
def transform_point(p: Vec3, M: Mat4) -> Vec3:
    p4 = np.array([p[0], p[1], p[2], 1.0], dtype=np.float64)
    return (p4 @ M)[:3]

#Biến đổi nhiều đỉnh
def transform_points(vertices: np.ndarray, M: Mat4) -> np.ndarray:
    if vertices.size == 0:
        return vertices.copy()
    ones = np.ones((vertices.shape[0], 1), dtype=np.float64)
    hom = np.hstack([vertices, ones])
    return (hom @ M)[:, :3]



### Phép chiếu và quan sát vật thể
def look_at_matrix(eye: Vec3, target: Vec3, up: Vec3 = np.array([0.0, 0.0, 1.0])) -> Mat4:
    eye_v = np.asarray(eye, dtype=np.float64)
    target_v = np.asarray(target, dtype=np.float64)
    up_v = np.asarray(up, dtype=np.float64)

    f = unit(eye_v - target_v)      # truc +Z cua camera (huong ra sau)
    r = unit(np.cross(up_v, f))     # truc +X cua camera (sang phai)
    u = np.cross(f, r)              # truc +Y cua camera (len tren)

    M = mat4_identity()
    M[0, :3] = r
    M[1, :3] = u
    M[2, :3] = f
    M[3, 0] = -dot(r, eye_v)
    M[3, 1] = -dot(u, eye_v)
    M[3, 2] = -dot(f, eye_v)
    return M

#Phep chieu phoi canh
def perspective_matrix(fov_deg: float, aspect: float, z_near: float, z_far: float) -> Mat4:
    t = math.tan(math.radians(fov_deg) * 0.5)
    M = np.zeros((4, 4), dtype=np.float64)
    M[0, 0] = 1.0 / (aspect * t)
    M[1, 1] = 1.0 / t
    M[2, 2] = -(z_far + z_near) / (z_far - z_near)
    M[2, 3] = -1.0
    M[3, 2] = -(2.0 * z_far * z_near) / (z_far - z_near)
    return M

#Phep chieu song song
def ortho_matrix(
    left: float, right: float,
    bottom: float, top: float,
    z_near: float, z_far: float,
) -> Mat4:
    M = mat4_identity()
    M[0, 0] = 2.0 / (right - left)
    M[1, 1] = 2.0 / (top - bottom)
    M[2, 2] = -2.0 / (z_far - z_near)
    M[3, 0] = -(right + left) / (right - left)
    M[3, 1] = -(top + bottom) / (top - bottom)
    M[3, 2] = -(z_far + z_near) / (z_far - z_near)
    return M

#Anh xa len man hinh
def project_to_screen(
    p: Vec3,
    modelview: Mat4,
    projection: Mat4,
    viewport: tuple[int, int, int, int] | np.ndarray,
) -> tuple[float, float, float] | None:
    p4 = np.array([p[0], p[1], p[2], 1.0], dtype=np.float64)
    clip = (p4 @ modelview) @ projection
    if abs(clip[3]) < 1e-12:
        return None
    ndc = clip[:3] / clip[3]
    vx, vy, vw, vh = viewport
    sx = vx + (ndc[0] + 1.0) * 0.5 * vw
    sy = vy + (ndc[1] + 1.0) * 0.5 * vh
    sz = (ndc[2] + 1.0) * 0.5
    # Chuyen goc Y tu duoi-len (OpenGL) sang tren-xuong
    return (float(sx), float(vh - sy), float(sz))