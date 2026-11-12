# GeoSpace 3D — Kế hoạch triển khai

> Đề tài: **Xây dựng phần mềm hỗ trợ giảng dạy hình học không gian 3D cấp THPT sử dụng Python và PyOpenGL**
> Kiến trúc: **A + B** — mọi thứ là đối tượng hình học độc lập (A), nhưng được nối bằng đồ thị phụ thuộc (B).
> Nguyên tắc số 1: **renderer không bao giờ tính toán hình học**, và **core không bao giờ import Qt/OpenGL**.

---

## 0. Ba quyết định kiến trúc chốt trước khi viết dòng code đầu tiên

### 0.1. Không có "hàm vẽ hình lập phương"

Sai lầm thường gặp: `def draw_cube()`, `def draw_pyramid()`, `def draw_prism()`… → 20 hình = 20 hàm, sửa 1 chỗ phải sửa 20 nơi.

Đúng: **một từ vựng constructor nhỏ, đóng kín**, đủ để biểu diễn mọi hình.

| Nhóm | Constructor | Ghi chú |
|---|---|---|
| Điểm | `fixed(x,y,z)` | điểm tự do |
| | `affine(Σ cᵢ·Pᵢ)` | **tổ hợp tuyến tính** — viên gạch quan trọng nhất |
| | `on_curve(C, t)` | điểm chạy trên đoạn/đường/tròn (t kéo được) |
| | `project(P, target)` | hình chiếu lên đường/mặt |
| | `intersect(a, b)` | giao điểm đường-đường, đường-mặt |
| Đường | `through(A, B)`, `parallel(d, P)`, `perp(plane, P)`, `perp_plane(line, P)` | |
| Mặt | `plane3(A,B,C)`, `plane_parallel(P, Q)`, `plane_perp(d, P)` | |
| Đa giác | `polygon([P₁..Pₙ])` | tự kiểm tra đồng phẳng |
| Đường tròn | `circle(center, r, normal)`, `circle3(A,B,C)` | cho trụ/nón/cầu |
| Khối | `solid(name, faces=[[ids]])` | **node nhóm + topology**, không phải hình vẽ |

`affine` một mình đã nuốt gần hết các phép dựng của SGK:

```
M = trung điểm AB        → 0.5·A + 0.5·B
N chia AB theo 1:2       → (2/3)·A + (1/3)·B
A' đối xứng A qua O      → 2·O − A
F của hình lập phương    → B + E − A          (không cần toạ độ cứng!)
G                        → C + E − A, với C = B + D − A
tịnh tiến theo v        → A + v
trọng tâm tam giác       → (A+B+C)/3
```

⇒ Hình lập phương/hình hộp/lăng trụ/chóp chỉ là **generator = macro sinh ra các node `affine` + `polygon` + `solid`**. Không có hình nào được "hard-code" ở tầng renderer.

```python
# generators/cube.py  — minh hoạ ý tưởng, không phải code cuối
# Input: A, B, D, E (4 đỉnh đủ xác định khối)
C = affine(B + D - A)
F = affine(B + E - A)
G = affine(C + E - A)
H = affine(D + E - A)
solid("ABCD.EFGH", faces=[ABCD, EFGH, ABFE, BCGF, CDHG, DAEH])
```

Đổi toạ độ A → C, F, G, H tự cập nhật theo. Đây chính là "parametric".

### 0.2. Đồ thị phụ thuộc (Dependency DAG) là trái tim của phần mềm

```
Object = { id, type, name, ctor, args, style, visible, locked, group }

args chứa id của object khác  ──►  cạnh của DAG
```

Mỗi lần sửa:
1. `mark_dirty(obj)` → lan xuống toàn bộ **dependent** (dùng reverse index `parent → children`).
2. Sắp xếp topo các node dirty → `evaluate()` lại theo thứ tự, ghi vào cache `obj.value`.
3. Nếu phát hiện chu trình khi tạo object → từ chối, báo lỗi ở console.
4. Bắn signal `scene_changed(ids)` → viewport chỉ upload lại VBO của các id đó, Object Manager chỉ refresh nhánh đó.

Không có bước này thì "sửa A, M tự chạy theo" không thể hoạt động — và cũng không thể lưu/load đúng (xem 0.3).

### 0.3. Lưu **quan hệ**, không lưu toạ độ kết quả

`.geo3d` = file zip chứa `project.json`:

```json
{
  "format": "geo3d", "version": 1,
  "meta": {"title": "Bài 1 - Hình chóp S.ABCD", "author": "...", "created": "..."},
  "camera": {"target": [0,0,0], "distance": 18, "yaw": 35, "pitch": 22, "mode": "perspective"},
  "objects": [
    {"id":"p1","type":"point","name":"A","ctor":"fixed","args":{"xyz":[0,0,0]},"style":{...}},
    {"id":"p2","type":"point","name":"M","ctor":"affine","args":{"terms":[{"c":0.5,"ref":"p1"},{"c":0.5,"ref":"p5"}]}},
    {"id":"s1","type":"solid","name":"S.ABCD","ctor":"solid","args":{"faces":[["p1","p2","p3","p4"],["p5","p1","p2"]]}}
  ]
}
```

Toạ độ hiện tại **không** được lưu (trừ `fixed`). Mở lại file → chạy lại DAG → M vẫn là trung điểm AB dù A đã bị chỉnh trong file.

---

## 1. Workflow phát triển (developer)

```
Sprint 0  Môi trường + khung app chạy được
Sprint 1  Viewport: Oxyz, orbit 360°, zoom, pan, lưới  ──►  demo "đồ hoạ sống"
Sprint 2  Geometry core + DAG + undo (pure Python, có test)  ──►  demo bằng script
Sprint 3  Render object thật: điểm/cạnh/mặt/đường khuất/nhãn/picking
Sprint 4  Generators + parser lệnh  ──►  gõ "hinh chop S.ABCD ..." là ra hình
Sprint 5  GUI đầy đủ: toolbar, Object Manager, Properties, đồng bộ chọn 2 chiều
Sprint 6  Save/Load/Export (.geo3d, PNG, PDF, OBJ)
Sprint 7  Tính năng giảng dạy: đo đạc, thiết diện, animation, explode, trình chiếu
Sprint 8  Đóng gói + tài liệu + video demo + bộ bài giảng mẫu
```

**Cổng kiểm soát:** hết Sprint 5 **đóng băng tính năng**. Từ đó chỉ sửa lỗi + làm Sprint 7.

### Quy tắc kỹ thuật bắt buộc

| Quy tắc | Lý do |
|---|---|
| `core/` chỉ import `numpy` (+ `math`), **không** Qt, **không** OpenGL | test bằng pytest không cần màn hình; đổi renderer không ảnh hưởng |
| Renderer chỉ đọc `scene`, không gọi hàm toán | tránh 2 nguồn sự thật |
| Mọi thao tác sửa scene đi qua `Command` (add/update/delete/group) | có undo/redo miễn phí: snapshot JSON của scene (nhỏ, vài chục KB) |
| Mỗi object có `id` ổn định, tên chỉ là nhãn | đổi tên A→A₁ không làm gãy phụ thuộc |
| Toạ độ tính bằng `float64` trong core, `float32` khi đẩy lên GPU | chính xác khi đo đạc, nhẹ khi render |

---

## 2. Cấu trúc thư mục (theo thứ tự triển khai)

```
GeoSpace3D/
├── main.py                      (1)
├── requirements.txt             (0)
├── core/                        ← pure python, có test
│   ├── vec.py                   (2)  Vec3, Plane, Line, helpers
│   ├── objects.py               (2)  Object, registry ctor, dataclass args
│   ├── ctors.py                 (2)  hiện thực từ vựng constructor (bảng 0.1)
│   ├── scene.py                 (2)  chứa object, DAG, dirty, evaluate, undo
│   ├── commands.py              (2)  AddObject/UpdateArgs/Delete/Group...
│   └── measure.py               (7)  distance, angle, dihedral, area, volume
├── generators/                  ← macro sinh node, KHÔNG vẽ
│   ├── polyhedron.py            (4)  cube, box, prism, pyramid, tetra, custom
│   └── surfaces.py              (4)  cylinder, cone, sphere
├── parser/
│   ├── lexer.py                 (4)
│   └── command_parser.py        (4)  "M = midpoint(A,B)", "cube ABCD.EFGH A=(1,0,0) ..."
├── renderer/
│   ├── gl_utils.py              (1)  shader, VAO/VBO, FBO
│   ├── camera.py                (1)  orbit, pan, zoom, persp/ortho
│   ├── axes.py                  (1)  Oxyz + lưới + tick
│   ├── renderer.py              (3)  point/segment/plane/polygon/solid, alpha, dashed
│   ├── picking.py               (3)  FBO id-color
│   └── text_overlay.py          (3)  nhãn bằng QPainter
├── gui/
│   ├── viewport.py              (1)  QOpenGLWidget, chuột, phím
│   ├── main_window.py           (5)  QMainWindow + dock
│   ├── toolbar.py               (5)
│   ├── object_manager.py        (5)  QTreeWidget + context menu
│   ├── properties_panel.py      (5)
│   ├── command_console.py       (4)
│   └── dialogs.py               (5)  wizard tạo khối, hộp thoại tô màu
├── project/
│   ├── serializer.py            (6)  scene ↔ dict, round-trip test
│   └── exporter.py              (6)  PNG, PDF, OBJ
├── tests/
│   ├── test_vec.py  test_dag.py  test_ctors.py  test_serializer.py  (2,4,6)
└── samples/                     (8)  .geo3d bài giảng mẫu
```

---

## 3. Chi tiết từng sprint + tiêu chí nghiệm thu (DoD)

### Sprint 0 — Môi trường (≈3 h)
- venv Python **3.12/3.13** (khuyến nghị, vì PyInstaller hỗ trợ chậm hơn Python mới; máy đang có 3.14 vẫn chạy được PyQt6 6.12 nhưng đóng gói sẽ khó).
- `pip install PyQt6 PyOpenGL numpy sympy pytest`.
- Cấu hình `QSurfaceFormat` (**phải set trước khi tạo `QApplication`**): OpenGL 3.3 Core, depth 24, samples 4.
- **DoD:** `python main.py` mở cửa sổ 1280×800, theme tối, log "GL 3.3 / renderer name".

### Sprint 1 — Viewport 360° (≈10 h)
Camera orbit: `yaw, pitch, distance, target`.
- Chuột trái kéo = xoay (clamp pitch ±89°), lăn = zoom (theo `distance`, không theo FOV), chuột phải/giữa kéo = pan trong mặt phẳng camera.
- Phím `Home` reset, `1/2/3` front/top/right, `0` phối cảnh, `5` bật/tắt ortho.
- Trục Oxyz có màu chuẩn (X đỏ, Y lục, Z lam), lưới mặt Oxy, tick + nhãn số bằng `QPainter`.
- **DoD:** một khung lập phương wireframe xoay mượt 60 FPS, không lật hình khi qua cực.

### Sprint 2 — Geometry core + DAG (≈15 h) ⭐ sprint quan trọng nhất
- `Vec3`, `Plane`, `Line` thuần numpy, toán tử `+ - * @`, `dot/cross/norm/unit`, `project`, `intersect_line_line`, `intersect_line_plane`, `plane_plane`.
- `Object` + registry `ctor` (dict `name → Callable(args, ctx) → value`).
- `Scene`: `add`, `update_args`, `delete`, `dependents(id)`, `evaluate(dirty)`, `topological_order`, phát hiện cycle, `to_dict/from_dict`.
- `Command` + `UndoStack` (snapshot).
- **DoD:** test pytest xanh cho: trung điểm, đối xứng, tỉ lệ, đổi A thì M/F/G/H đổi theo, xoá A thì các object phụ thuộc bị xoá cascade (có cảnh báo), round-trip serialize.

### Sprint 3 — Render object thật (≈15 h)
- Điểm: sprite tròn (hoặc `GL_POINTS` + shader làm tròn), kích thước theo pixel không theo zoom.
- Cạnh/đoạn: line strip, độ dày cấu hình; **nét đứt tự sinh bằng hình học** (chia thành các dash) — không dùng `GL_LINE_STIPPLE` vì Core Profile không có.
- Mặt: tam giác hoá polygon (fan cho đa giác lồi — đủ cho SGK), alpha + **sort theo chiều sâu tâm mặt** để trong suốt không bị loang.
- **Đường khuất**: pass 1 vẽ mặt chỉ ghi depth; pass 2 vẽ cạnh: đoạn nào `depth > stored` → vẽ nét đứt màu nhạt, ngược lại nét liền. Đây là tính năng "ăn điểm" khi bảo vệ.
- Picking bằng FBO: render mỗi object 1 màu = id, đọc pixel tại con trỏ → hover highlight + click select.
- Nhãn chữ (A, B, M, "S.ABCD") bằng `QPainter` chồng lên sau `paintGL` — tránh phải kéo thêm font engine.
- **DoD:** click vào đỉnh A trong 3D → phát signal `object_selected("p1")`.

### Sprint 4 — Generator + parser (≈12 h)
- Generator nhận tham số linh hoạt: `cube(A=(1,0,0), edge=2, dirs=[ex,ey,ez])` **hoặc** `cube(A,B,D,E)`; `pyramid(base=[A,B,C,D], apex=S)`; `prism(base=[...], vec=v)`; `cylinder(center, r, h, axis)`, `cone`, `sphere`, `tetra`.
- Parser: tokenizer đơn giản + grammar cho 2 dạng lệnh
  - khai báo đối tượng: `M = midpoint(A, B)`, `d = line(A, B)`, `(P) = plane(A, B, C)`
  - macro: `cube ABCD.EFGH  A=(1,0,0)  B=(3,0,0)  D=(1,2,0)  E=(1,0,2)`
- Báo lỗi có ngữ cảnh: *"dòng 3: điểm 'Q' chưa được khai báo"*, gợi ý tên gần đúng.
- Autocomplete + history (`↑`) trong console.
- **DoD:** gõ 4 dòng lệnh là ra hình chóp có trung điểm M, đoạn MN, đúng như workflow mẫu bên dưới.

### Sprint 5 — GUI đầy đủ (≈18 h)
Bố cục: trái = thanh công cụ dọc + console; giữa = viewport; phải = Object Manager (trên) + Properties (dưới).

| Panel | Nội dung |
|---|---|
| Toolbar | Chọn · Điểm · Trung điểm · Đoạn · Đường · Mặt · Đa giác · Khối (▾) · Đo · Thiết diện · Xoá |
| Object Manager | cây nhóm `Points / Segments / Lines / Planes / Solids / Generated / Measurements`; mỗi dòng: checkbox hiện/ẩn, icon màu, tên; context menu: Rename, Color, Opacity, Lock, Delete, Duplicate, **Edit definition** (sửa `M = midpoint(A,B)` → `midpoint(A,C)` và cả cây tự cập nhật) |
| Properties | toạ độ x/y/z (spinbox, chỉ bật với điểm `fixed`), màu, độ dày, opacity, hiện nhãn, hiện toạ độ |
| Status bar | con trỏ 3D, số object, FPS |

Đồng bộ 2 chiều: chọn trong cây → highlight + camera không đổi; click trong 3D → cây tự chọn + scroll tới.
**DoD — "bài demo 60 giây"** (dùng làm acceptance test cuối):
> Tạo chóp S.ABCD → M = midpoint(SA) → N = midpoint(SC) → đoạn MN → ẩn mặt bên SCD → đổi màu mặt đáy → kéo S lên cao → M, N, MN chạy theo → undo 3 lần → save → new → load lại y hệt.

### Sprint 6 — Lưu / tải / xuất (≈8 h)
`.geo3d` (zip) + autosave 60 s + recent files; export PNG 2× (supersampling), PDF (ảnh + bảng object + số đo), OBJ (chỉ các `solid`, để in 3D nếu muốn).
**DoD:** round-trip test: save → load → `scene.to_dict()` giống hệt.

### Sprint 7 — Tính năng giảng dạy (≈20 h, chọn lọc theo thời gian còn lại)
Ưu tiên: **thiết diện** > đo khoảng cách/góc > **animation** > explode > trình chiếu.
- Thiết diện: mặt phẳng ∩ khối **lồi** = cắt đa giác bằng các nửa không gian (Sutherland–Hodgman 3D) → ra đa giác, tô màu, hiện diện tích. Khối lõm: cắt từng cạnh rồi sắp thứ tự.
- Animation: tham số `t` (điểm chạy trên cạnh, mặt phẳng quét, chiều cao chóp) + timeline play/pause + auto-rotate camera.
- Explode: dịch mỗi mặt theo pháp tuyến `k·n` (k kéo bằng slider).

### Sprint 8 — Đóng gói & hồ sơ (≈10 h)
PyInstaller one-folder; `HUONG_DAN.md`; 5–8 file `.geo3d` mẫu (chóp đều, lăng trụ đứng, thiết diện, góc nhị diện…); video demo 3–5 phút; hình cho báo cáo (use-case, kiến trúc, DAG, ảnh chụp).

---

## 4. Workflow người dùng cuối (chuẩn để test)

```
1. New Project
2. Console:  A=(0,0,0)  B=(4,0,0)  D=(0,4,0)  S=(2,2,5)
             pyramid S.ABCD  base=A,B,B+D-A,D  apex=S
3. Console:  M = midpoint(S, A)
             N = midpoint(S, C)
             MN = segment(M, N)
4. 3D: xoay 360°, thấy MN là đường trung bình của △SAC
5. Properties: đổi S.z = 8 → cả hình cập nhật tức thì
6. Object Manager: ẩn mặt (SCD), đổi màu (ABCD), khoá (S)
7. Save → Bai1.geo3d ; New ; Open → đúng như cũ, quan hệ còn nguyên
8. Export PDF → dán vào giáo án
```

---

## 5. Rủi ro & cách xử lý trước

| Rủi ro | Xử lý |
|---|---|
| PyOpenGL + Qt lỗi context / đen th.v. | set `QSurfaceFormat` trước `QApplication`; chỉ gọi GL trong `paintGL/initializeGL`; dùng Core Profile 3.3 + shader, không dùng immediate mode |
| Chữ trong 3D | không nhúng font engine → dùng `QPainter` overlay |
| Nét đứt / line width | Core Profile bỏ `LINE_STIPPLE`, `glLineWidth>1` không đảm bảo → sinh dash bằng hình học, hoặc render line thành quad nếu cần dày |
| Đa giác không đồng phẳng (nhập sai) | kiểm tra sai số 1e-9, cảnh báo, vẫn vẽ với mặt phẳng best-fit |
| Object phụ thuộc bị xoá | cascade delete + hộp thoại xác nhận liệt kê object sẽ mất |
| Scope creep (tham animation khi core chưa xong) | cổng đóng băng sau Sprint 5 |
| Python 3.14 + PyInstaller | làm venv 3.12/3.13 từ Sprint 0 |
| Hiệu năng khi 500+ object | VBO/object, chỉ re-upload object dirty; batch theo material; đủ nhanh cho phạm vi THPT |

---

## 6. Tổng thời lượng

| Sprint | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Σ |
|---|---|---|---|---|---|---|---|---|---|---|
| Giờ | 3 | 10 | 15 | 15 | 12 | 18 | 8 | 20 | 10 | **≈111 h** |

Chia 3 người ≈ 37 h/người ≈ 5–6 tuần (12 h/tuần). Một người ≈ 8–10 tuần.

**Mốc bắt buộc có demo chạy được:** hết Sprint 1 (đồ hoạ), Sprint 3 (hình thật + click), Sprint 5 (phần mềm dùng được), Sprint 6 (nộp được).
