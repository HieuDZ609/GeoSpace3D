# GeoSpace 3D — Kế hoạch bản DEMO (bản đơn giản để nộp bài tập nhóm)

> Bản đầy đủ (111 h, sản phẩm thật) đã tách sang `PLAN_FULL.md` — dùng làm mục **"Hướng phát triển"** trong báo cáo, không làm.
> Bản này: **~35 h, 3 người ≈ 12 h/người ≈ 2–3 tuần**, đủ để demo trước lớp.

> **Trạng thái: ĐÃ HOÀN THÀNH** (xem `README.md`). Đã làm vượt kế hoạch: trụ/nón/cầu,
> điểm chạy trên cạnh + animation, đo khoảng cách/góc, undo/redo, auto-rotate, xuất PNG.

---

## 1. Phạm vi: giữ gì, cắt gì

| Giữ (demo được) | Cắt (ghi vào "hướng phát triển") |
|---|---|
| Trục Oxyz + lưới + nhãn | Parser ngôn ngữ lệnh / console |
| Camera orbit 360°, zoom, pan, ortho | Picking bằng FBO (thay bằng click chọn điểm đơn giản) |
| Điểm, đoạn, đường, mặt phẳng, đa giác | Thiết diện, góc nhị diện, thể tích |
| Khối: lập phương, hộp chữ nhật, chóp, lăng trụ | Trụ / nón / cầu (chỉ làm nếu còn thời gian) |
| Quan hệ: tự do, trung điểm, chia đoạn, đối xứng | Animation, explode, trình chiếu |
| Cây layer: ẩn/hiện, đổi màu, đổi tên, xoá | Export PDF / OBJ, đóng gói PyInstaller |
| Save / Load JSON | Undo/redo (nếu rảnh thì thêm, ~20 dòng) |
| Đường khuất nét đứt (rất ăn điểm, chỉ ~30 dòng) | Đo khoảng cách/góc (tuỳ thời gian) |

> Nguyên tắc: **mỗi tính năng phải demo được trong 5 giây trước lớp**, không có tính năng nào "chỉ chạy trong log".

---

## 2. Đơn giản hoá kỹ thuật (khác bản đầy đủ)

| Hạng mục | Bản đầy đủ | **Bản demo** | Tiết kiệm |
|---|---|---|---|
| OpenGL | Core 3.3 + shader + VBO | **Immediate mode** (`glBegin/glEnd`), compat profile | ~200 dòng, ít lỗi context |
| Nét đứt | tự sinh dash | `glLineStipple` (có sẵn) | ~40 dòng |
| Cập nhật phụ thuộc | dirty + cache tăng dần | **evaluate lại toàn scene** theo topo mỗi lần sửa (<500 object vẫn tức thì) | ~80 dòng |
| Picking | FBO id-color | chiếu các điểm ra màn hình, chọn điểm gần con trỏ nhất | ~90 dòng |
| Lưu file | `.geo3d` (zip) | `.json` thuần, 1 file | ~50 dòng |
| Cấu trúc | 30 file | **7 file** | — |

**Lưu ý:** đây là đánh đổi có chủ ý, viết đúng 1 câu trong báo cáo: *"Bản demo dùng immediate mode để tập trung vào mô hình dữ liệu hình học; kiến trúc đã tách renderer khỏi core nên có thể chuyển sang VBO/shader mà không sửa core."* → biến điểm yếu thành điểm cộng.

---

## 3. Mô hình dữ liệu (giữ nguyên tinh thần A+B, viết gọn)

```python
Object:
  id, type, name, ctor, args, color, visible, group

ctor:  "fixed"    args = {"xyz": [x,y,z]}
       "affine"   args = {"terms": [[0.5,"p1"],[0.5,"p2"]]}     # M = trung điểm A B
       "segment"  args = {"a":"p1", "b":"p2"}
       "line"     args = {"a":"p1", "b":"p2"}
       "plane"    args = {"pts":["p1","p2","p3"]}
       "face"     args = {"pts":["p1","p2","p3","p4"]}          # đa giác, có tô màu
       "solid"    args = {"faces":[["p1",...],...]}             # node nhóm
```

- `affine` đủ cho: trung điểm `0.5A+0.5B`, chia 1:2 `⅔A+⅓B`, đối xứng `2O−A`, và **đỉnh còn lại của lập phương** `F = B+E−A`.
- Sửa A ⇒ `evaluate()` chạy lại theo thứ tự topo ⇒ M, F, mặt, khối tự đổi. Đây là toàn bộ "phép thuật" của đề tài, **chỉ ~30 dòng**.
- Generator = hàm sinh ra các Object trên: `gen_cube(A,B,D,E)`, `gen_box(A, dx,dy,dz)`, `gen_pyramid(base_ids, S)`, `gen_prism(base_ids, v)`. Không có hàm vẽ nào cho từng hình.

---

## 4. Cấu trúc file (7 file, thứ tự làm)

```
GeoSpace3D/
├── main.py               (1)  QApplication + MainWindow
├── requirements.txt      (0)  PyQt6, PyOpenGL, numpy
├── core/
│   ├── math3d.py         (1)  Vec3, pháp tuyến, projection to screen
│   ├── scene.py          (2)  Object, Scene, evaluate, save/load JSON   ← làm kỹ + test
│   └── generators.py     (2)  cube, box, pyramid, prism
├── gui/
│   ├── viewport.py       (1)  QOpenGLWidget: camera, axes, draw, chuột, click điểm
│   ├── main_window.py    (3)  toolbar + cây layer + panel thuộc tính
│   └── dialogs.py        (3)  hộp thoại nhập toạ độ / tạo khối
└── tests/test_core.py    (2)  pytest: trung điểm, affine, đổi A, save/load
```

---

## 5. 4 mốc triển khai

### Mốc 1 — Khung + Viewport (≈10 h) — *demo được: đồ hoạ sống*
- venv, `pip install PyQt6 PyOpenGL numpy pytest`
- `QSurfaceFormat`: depth 24, samples 4 (**set trước `QApplication`**)
- Camera orbit: `yaw, pitch, dist, target`; chuột trái xoay, lăn zoom, phải pan; `Home` reset, `5` bật/tắt ortho
- Vẽ: trục X đỏ / Y lục / Z lam, lưới Oxy, tick + nhãn số bằng `QPainter`, 1 khung lập phương cứng để test xoay

**DoD:** xoay 360° không lật, 60 FPS, nhãn không méo.

### Mốc 2 — Core + Generator (≈9 h) — *demo được: sửa A, hình tự đổi*
- `math3d.py`, `scene.py` (add/update/delete/evaluate/topological/save/load), `generators.py`
- pytest: trung điểm đúng, đổi A ⇒ M đổi, xoá A ⇒ object phụ thuộc bị xoá kèm cảnh báo, save→load giống hệt

**DoD:** chạy `pytest` xanh; script tạo lập phương, đổi A sang (5,0,0), in ra F/G/H mới đúng.

### Mốc 3 — GUI dùng được (≈12 h) — *demo được: phần mềm*
- Toolbar: Chọn · Điểm · Trung điểm · Đoạn · Đường · Mặt · Khối(▾) · Xoá
- Cây layer theo nhóm (Points / Segments / Faces / Solids): checkbox ẩn/hiện, menu chuột phải (đổi tên, màu, xoá)
- Panel thuộc tính: sửa x/y/z của điểm tự do → cả hình cập nhật ngay
- Click điểm trong 3D → tự chọn trong cây (và ngược lại)
- Vẽ mặt trong suốt + **đường khuất nét đứt** (vẽ mặt chỉ ghi depth, rồi vẽ cạnh nét liền/đứt)

**DoD:** chạy trọn kịch bản demo bên dưới, không crash.

### Mốc 4 — Lưu/tải + đánh bóng (≈6 h)
- Save / Save As / Open (`Ctrl+S`, `Ctrl+O`), tiêu đề cửa sổ hiện tên file
- 3 file `.json` mẫu: chóp đều S.ABCD, lập phương có M trung điểm, lăng trụ đứng
- Ảnh chụp màn hình cho báo cáo, sửa lỗi vặt

---

## 6. Kịch bản demo 60 giây (dùng để tự kiểm tra & để thuyết trình)

1. Mở app → thấy Oxyz, xoay thử 360°.
2. Tạo chóp `S.ABCD` (nhập toạ độ đáy + S).
3. Bấm **Trung điểm** → chọn S, A → có M; chọn S, C → có N.
4. Bấm **Đoạn** → M, N → hiện MN (đường trung bình △SAC).
5. Mở panel, kéo S.z từ 5 → 8 → **M, N, MN chạy theo ngay** (điểm nhấn của đề tài).
6. Ẩn mặt bên, đổi màu đáy, bật nét đứt cho cạnh khuất.
7. Save → New → Open lại → y hệt.

---

## 7. Phân công gợi ý (3 người)

| Người | Việc | Mốc |
|---|---|---|
| A | `viewport.py`: camera, trục, vẽ, click điểm | 1, 3 |
| B | `scene.py` + `generators.py` + test | 2 |
| C | `main_window.py` + `dialogs.py` + save/load + dữ liệu mẫu | 3, 4 |

Ai cũng phải đọc `PLAN.md` này và thống nhất `Object`/`ctor` ở Mốc 2 **trước khi** làm song song, nếu không sẽ lệch interface.

---

## 8. Rủi ro cần tránh (bản demo)

- **Đừng** làm parser lệnh, thiết diện, animation → hết thời gian, mất demo.
- **Đừng** dùng Core Profile nếu chưa quen shader → context đen, mất 1 buổi.
- Nhãn chữ trong 3D: dùng `QPainter` chồng lên, đừng nhúng font engine.
- Xoá object phải cascade (nếu không, `evaluate` sẽ crash vì thiếu ref) — làm ngay ở Mốc 2.
- Đóng gói `.exe`: **không bắt buộc** cho bài tập nhóm, chỉ cần chạy `python main.py` trên máy demo. Nếu bắt buộc thì làm venv Python 3.12 từ đầu.
