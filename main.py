import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QSurfaceFormat
from gui.main_window import MainWindow


def main():
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    # Khong bat MSAA: tren mot so driver (Mesa/XWayland) FBO multisample
    # lam grabFramebuffer tra ve anh den. Da co LINE_SMOOTH/POINT_SMOOTH.
    fmt.setSamples(0)
    fmt.setVersion(2, 1)            # compat profile -> dung duoc immediate mode
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()