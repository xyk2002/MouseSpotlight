# @File    :   MouseSpotlight.py
# @Time    :   2025/05/14 23:05:28
# @Author  :   XKun
# @Version :   1.0
# @Contact :   3031657892@qq.com
# @GitHub  :   https://github.com/xyk2002
# @Project :   https://github.com/xyk2002/MouseSpotlight
# @License :   MIT LICENSE



import os
import sys
import time

from pynput import keyboard
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (QAction, QBrush, QColor, QCursor, QIcon, QPainter,
                         QPainterPath, QPen, QRadialGradient)
from PyQt6.QtWidgets import (QApplication, QMenu, QMessageBox, QSystemTrayIcon,
                             QWidget)


class Resources:
    
    @staticmethod
    def getPath(filename):

        bundleDir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        path = os.path.join(bundleDir, filename)

        return path


class KeyboardListener(QThread):
    toggleSignal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.lastPress = 0
        self.isCtrlPressed = False
        self.isCtrlRelease = False


    def run(self):

        def keyHandler(key):
            if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
                if not self.isCtrlPressed:
                    self.isCtrlPressed = True
                    self.lastPress = time.time()
                    return

                if time.time() - self.lastPress < 0.3:
                    if self.isCtrlRelease and self.isCtrlPressed:
                        self.toggleSignal.emit()
                        self.isCtrlRelease = False
                        self.isCtrlPressed = False
                else:
                    self.isCtrlRelease = False
                    self.isCtrlPressed = False
            
            else:
                self.isCtrlRelease = False
                self.isCtrlPressed = False

        def setCtrlRelease(key):
            if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r] and self.isCtrlPressed:
                self.isCtrlRelease = True

        with keyboard.Listener(on_press=keyHandler, on_release=setCtrlRelease) as listener:
            listener.join()


class MouseSpotlight(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initAnimation()
        self.initListener()
        self.initTray()
    
        self.radius = 800
        self.targetRadius = 80
        self.opacity = 0     
        self.targetOpacity = 0
        self.animating = False
        self.visible = False

        self.animationDuration = 0.5 
        self.maxOpacity = 200        
        self.currentOpacity = 0

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.showFullScreen()
        self.hide()
        

    def initAnimation(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)
        self.timer.start(16)


    def initListener(self):
        self.listener = KeyboardListener()
        self.listener.toggleSignal.connect(self.toggleSpotlight)
        self.listener.start()


    def initTray(self):
        self.trayMenu = QMenu()
        Information = QAction("Information", self)
        Information.triggered.connect(self.information)
        self.trayMenu.addAction(Information)
        self.trayMenu.addSeparator()
        Exit = QAction("Exit", self)
        Exit.triggered.connect(self.exitAction)
        self.trayMenu.addAction(Exit)

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(Resources.getPath("logo.png")))        
        self.tray.setContextMenu(self.trayMenu)
        self.tray.show()
        self.tray.showMessage(
            "MouseSpotlight",
            "The program is running in the background. (Author: XKun)",
            QIcon(Resources.getPath("logo.png")),
            3000
        )
        self.tray.activated.connect(self.openMenu)


    def openMenu(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.information()


    def information(self):
        QMessageBox.information(None, "MouseSpotlight", """This is an application used on Windows to find the position of the mouse. By pressing the Ctrl key twice in a row quickly, a simulated light focusing method is activated to highlight the position of the mouse cursor.
The address of the project: https://github.com/xyk2002/MouseSpotlight
My GitHub:https://github.com/xyk2002/
Thank you for using it!
        """)


    def exitAction(self):
        self.tray.hide()
        QApplication.quit()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        cursorPos = QCursor.pos()
        localPos = self.mapFromGlobal(cursorPos).toPointF()
        mainRadius = float(self.radius)
        penWidth = mainRadius * 0.06

        gradient = QRadialGradient(localPos, mainRadius + penWidth)
        gradient.setColorAt(0.95, QColor(255, 255, 255, int(180 * self.currentOpacity / self.maxOpacity)))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(QBrush(gradient), penWidth))
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(localPos, mainRadius, mainRadius)
        
        mainPath = QPainterPath()
        mainPath.addRect(self.rect().toRectF())
        ellipsePath = QPainterPath()
        ellipsePath.addEllipse(localPos, mainRadius, mainRadius)
        maskPath = mainPath.subtracted(ellipsePath)
        painter.fillPath(maskPath, QColor(0, 0, 0, int(self.currentOpacity)))


    def updateAnimation(self):
        now = time.time()
        
        if self.animating:
            elapsed = now - self.animationStartTime
            progress = min(elapsed / self.animationDuration, 1.0)
            eased = self.easeInOutBezierCurve(progress)

            self.radius = self.startRadius + (self.targetRadius - self.startRadius) * eased
            self.currentOpacity = self.startOpacity + (self.targetOpacity - self.startOpacity) * eased
        
            self.update()

            if progress >= 1.0:
                self.animating = False
                if not self.visible:
                    self.hide()
        else:
            self.update()


    def easeInOutBezierCurve(self, t):
        return 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2)**3 / 2


    def toggleSpotlight(self):
        if self.visible:
            self.startAnimation(
                startRadius=self.radius,
                targetRadius=800,
                startOpacity=self.currentOpacity,
                targetOpacity=0
            )
            self.visible = False
        else:
            self.show()
            self.raise_()
            self.startAnimation(
                startRadius=800,
                targetRadius=80,
                startOpacity=0,
                targetOpacity=self.maxOpacity
            )
            self.visible = True


    def startAnimation(self, startRadius, targetRadius, startOpacity, targetOpacity):
        self.animationStartTime = time.time()
        self.animating = True
        
        self.startRadius = startRadius
        self.targetRadius = targetRadius
        self.radius = startRadius

        self.startOpacity = startOpacity
        self.targetOpacity = targetOpacity
        self.currentOpacity = startOpacity




if __name__ == "__main__":
    QApplication.setApplicationName("MouseSpotlight")
    app = QApplication(sys.argv)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray", "The system does not support tray ICONS!")
        sys.exit(1)
    app.setQuitOnLastWindowClosed(False)
    main = MouseSpotlight()
    sys.exit(app.exec())
