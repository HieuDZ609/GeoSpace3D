from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from core.math3d import Mat4, Vec3, transform_points

RGBA = tuple[float, float, float, float]
def normalize_rgba(color: tuple[float, ...] | list[float]) -> RGBA:
    c = [float(x) for x in color]
    if len(c) == 3:
        return (c[0], c[1], c[2], 1.0)
    return (c[0], c[1], c[2], c[3])

#Đoạn thẳng qua 2 diem
@dataclass
class SegmentData:
    a: Vec3
    b: Vec3

#Mat phang duoc xac dinh boi vector phap tuyen va 1 diem
@dataclass
class PlaneData:
    origin: Vec3
    normal: Vec3
    d: float

#Mô hình hóa đối tượng: Khung kết nối
@dataclass
class WireFrame:
    vertices: np.ndarray
    edges: list[tuple[int, int]] = field(default_factory=list)

    def transformed(self, M: Mat4) -> WireFrame:
        return WireFrame(
            vertices=transform_points(self.vertices, M),
            edges=list(self.edges),
        )

#Mô hình hóa đối tượng: FaceModel
@dataclass
class FaceModel:
    vertices: np.ndarray                                 
    faces: list[list[int]] = field(default_factory=list)

    def transformed(self, M: Mat4) -> FaceModel:
        return FaceModel(
            vertices=transform_points(self.vertices, M),
            faces=[list(f) for f in self.faces],
        )

#Khoi 3D hoan chinh
@dataclass
class SolidModel:
    face_model: FaceModel
    wireframe: WireFrame

    def transformed(self, M: Mat4) -> SolidModel:
        return SolidModel(
            face_model=self.face_model.transformed(M),
            wireframe=self.wireframe.transformed(M),
        )
# Hiển thi khoảng cách hoặc góc
@dataclass
class MeasureData:
    anchor: Vec3
    text: str
    segment: SegmentData | None = None

GeomValue = Vec3 | SegmentData | PlaneData | WireFrame | FaceModel | SolidModel | MeasureData

#Node trong do thi
NodeKind = Literal[
    "point", "segment", "line", "plane",
    "wireframe", "face", "solid", "surface", "measure",
]


@dataclass
class Node:
    id: str
    kind: NodeKind
    name: str
    ctor: str
    params: dict[str, Any] = field(default_factory=dict)
    color: RGBA = (0.9, 0.9, 0.9, 1.0)
    visible: bool = True
    group: str = ""
    value: GeomValue | None = field(default=None, repr=False)
    error: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.color = normalize_rgba(self.color)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "ctor": self.ctor,
            "params": self.params,
            "color": list(self.color),
            "visible": self.visible,
            "group": self.group,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Node:
        raw_params = d.get("params") if "params" in d else d.get("args", {})
        return Node(
            id=d["id"],
            kind=d["kind"],
            name=d["name"],
            ctor=d["ctor"],
            params=raw_params,
            color=normalize_rgba(d.get("color", (0.9, 0.9, 0.9, 1.0))),
            visible=d.get("visible", True),
            group=d.get("group", ""),
        )