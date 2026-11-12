from PyQt6.QtWidgets import (QDialog, QDoubleSpinBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout)


class AddPointDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Them diem")
        v = QVBoxLayout(self)
        r = QHBoxLayout()
        r.addWidget(QLabel("Ten"))
        self.name = QLineEdit("P")
        r.addWidget(self.name)
        v.addLayout(r)
        self.spins = []
        for ax in ("X", "Y", "Z"):
            r = QHBoxLayout()
            r.addWidget(QLabel(ax))
            sp = QDoubleSpinBox()
            sp.setRange(-100, 100)
            sp.setDecimals(3)
            r.addWidget(sp)
            v.addLayout(r)
            self.spins.append(sp)
        b = QPushButton("OK")
        b.clicked.connect(self.accept)
        v.addWidget(b)

    def get(self):
        return self.name.text().strip() or "P", [s.value() for s in self.spins]


class CreateSolidDialog(QDialog):
    def __init__(self, parent, kind):
        super().__init__(parent)
        self.kind = kind
        self.setWindowTitle(f"Tao {kind}")
        v = QVBoxLayout(self)

        # toa do diem A / tam
        r = QHBoxLayout()
        r.addWidget(QLabel("A / tam (x y z)"))
        self.ax = QDoubleSpinBox(); self.ay = QDoubleSpinBox(); self.az = QDoubleSpinBox()
        for sp in (self.ax, self.ay, self.az):
            sp.setRange(-100, 100)
            r.addWidget(sp)
        v.addLayout(r)

        def spin_row(label, value, lo=0.1, hi=200.0, dec=2):
            rr = QHBoxLayout()
            rr.addWidget(QLabel(label))
            sp = QDoubleSpinBox()
            sp.setValue(value)
            sp.setRange(lo, hi)
            sp.setDecimals(dec)
            rr.addWidget(sp)
            v.addLayout(rr)
            return sp

        if kind == "cube":
            self.edge = spin_row("Canh", 2.0)
        elif kind == "box":
            self.dx = spin_row("dx", 2.0)
            self.dy = spin_row("dy", 2.0)
            self.dz = spin_row("dz", 2.0)
        elif kind in ("pyramid", "prism"):
            self.side = spin_row("Canh day", 4.0)
            self.height = spin_row("Chieu cao", 5.0)
        elif kind in ("cylinder", "cone"):
            self.side = spin_row("Ban kinh", 2.0)
            self.height = spin_row("Chieu cao", 4.0)
        elif kind == "sphere":
            self.side = spin_row("Ban kinh", 2.0)

        b = QPushButton("OK")
        b.clicked.connect(self.accept)
        v.addWidget(b)

    def get(self):
        A = (self.ax.value(), self.ay.value(), self.az.value())
        out = {"A": A}
        for attr in ("edge", "dx", "dy", "dz", "side", "height"):
            val = getattr(self, attr, None)
            if isinstance(val, QDoubleSpinBox):
                out[attr] = val.value()
        return out
