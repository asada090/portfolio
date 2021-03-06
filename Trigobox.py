#!/usr/bin/env python3
from math import sin, cos, radians
import sys
from os import path, remove
from time import sleep
from PyQt5.QtGui import QPainter, QPalette, QPen, QColor, QBrush, QIcon
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
                             QSizePolicy, QApplication, QSlider, QLabel,
                             QPushButton, QCheckBox, QFileDialog, QMessageBox,
                             QProgressDialog, QColorDialog)
from PyQt5.QtCore import (QSize, QTimer, QPointF, Qt, QLineF, QByteArray,
                          QBuffer, QIODevice)
EXPORT_AVAILABLE = True
try:
    import imageio
except ImportError:
    print("Animation video export will be unavailable because you are missing imageio module")
    EXPORT_AVAILABLE = False

X_MULT_DEF = 1
Y_MULT_DEF = 1
DOT_SIZE_DEF = 6
NUM_DOTS_DEF = 40
ANGLE_FACTOR_DEF = 360
HALFMAX_DEF = 180
SPEED_MULT_DEF = 3
DELAY_DEF = 35
AXES_DEF = False
JOIN_ENDS_DEF = False
DRAW_AXES_DEF = False
COL1_DEF = QColor.fromRgb(0, 180, 0)
COL2_DEF = QColor.fromRgb(0, 0, 180)
LINES_DEF = False
CONNECT_LINES_DEF = False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = path.abspath(".")

    return path.join(base_path, relative_path)

def interpolate_hsv(col1, col2, num_middle):
    if num_middle < 0:
        raise ValueError

    assert col1.isValid()
    assert col2.isValid()

    start_h = col1.hsvHue() % 360
    start_s = col1.hsvSaturation() % 256
    start_v = col1.value() % 256

    delta_h = (col2.hsvHue() % 360) - start_h
    if delta_h < -180:
        delta_h = 360 + delta_h
    elif delta_h > 180:
        delta_h = - 360 + delta_h

    delta_s = (col2.hsvSaturation() % 256) - start_s
    delta_v = (col2.value() % 256) - start_v

    yield col1
    for i in range(1, num_middle+1):
        frac = i/num_middle
        yield QColor.fromHsv(
            (start_h + delta_h*frac) % 360,
            (start_s + delta_s*frac) % 256,
            (start_v + delta_v*frac) % 256,
        )
    yield col2


class DotsWidget(QWidget):

    def __init__(self):
        super().__init__()
        pal = QPalette()
        pal.setColor(QPalette.Background, QColor("#fff"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.frame_no = 1
        self.angle_factor = ANGLE_FACTOR_DEF
        self.num_dots = NUM_DOTS_DEF
        self.dot_size = DOT_SIZE_DEF
        self.x_multiplier = X_MULT_DEF
        self.y_multiplier = Y_MULT_DEF
        self.halfmax = HALFMAX_DEF
        self.speedmult = SPEED_MULT_DEF
        self.draw_axes = AXES_DEF
        self.join_end_dots = JOIN_ENDS_DEF
        self.col1 = COL1_DEF
        self.col2 = COL2_DEF
        self.draw_lines = LINES_DEF
        self.connect_lines = CONNECT_LINES_DEF

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(400, 400)

    def _try_update_frame(self):
        if self.parent().speedmult_slider.value() == 0:
            self.frame_no -= 1
            self.next_animation_frame()

    def change_angle_factor(self, value):
        self.parent().a_f_slider_val_label.setText(str(value))
        self.angle_factor = value
        self._try_update_frame()

    def change_halfmax(self, value):
        self.parent().halfmax_slider_val_label.setText(str(value))
        self.halfmax = value
        self._try_update_frame()

    def change_speedmult(self, value):
        self.parent().speedmult_slider_val_label.setText(str(value))
        if value == 0:
            self.timer.stop()
            self._try_update_frame()
            return
        if not self.timer.isActive():
            self.timer.start(self.parent().delay_slider.value())

        self.speedmult = value

    def change_draw_axes(self, value):
        self.draw_axes = value
        self._try_update_frame()

    def change_join_end_dots(self, value):
        self.join_end_dots = value
        self._try_update_frame()

    def change_num_dots(self, value):
        self.parent().num_dots_slider_val_label.setText(str(value))
        self.num_dots = value
        self._try_update_frame()

    def change_dot_size(self, value):
        self.parent().dot_size_slider_val_label.setText(str(value))
        self.dot_size = value
        self._try_update_frame()

    def change_x_multiplier(self, value):
        self.parent().x_multiplier_slider_val_label.setText(str(value))
        self.x_multiplier = value
        self._try_update_frame()

    def change_y_multiplier(self, value):
        self.parent().y_multiplier_slider_val_label.setText(str(value))
        self.y_multiplier = value
        self._try_update_frame()

    def change_lines_state(self, value):
        self.draw_lines = value
        self.parent().connect_lines_checkbox.setEnabled(value)
        self._try_update_frame()

    def change_connect_lines(self, value):
        self.connect_lines = value
        self._try_update_frame()


    def next_animation_frame(self):
        self.update()
        self.frame_no += 1

    def export_video(self):
        if not EXPORT_AVAILABLE:
            msgbox = QMessageBox(QMessageBox.Information,
                                 "Export not available",
                                 "`imageio` and `ffmpeg` must be installed to export videos")
            return msgbox.exec()

        if not self.timer.isActive():
            msgbox = QMessageBox(QMessageBox.Warning,
                                 "Cannot export animation",
                                 "Cannot export video when speed is 0")
            return msgbox.exec()

        location = QFileDialog.getSaveFileName(self,
                                               "Choose export location",
                                               filter="Video (*.mp4)")

        location = location[0]
        if location == '':
            # No file selected
            msgbox = QMessageBox(QMessageBox.Information,
                                 "Export cancelled",
                                 "No export file given")
            return msgbox.exec()

        if not location.endswith('.mp4'):
            location += '.mp4'
        progress_box = QProgressDialog(
            "Recording export video.\nNote that the larger the period value, "
            "the longer the video.",
            "Cancel",
            1,
            self.halfmax * 2 + 1,
            self)
        progress_box.setWindowModality(Qt.WindowModal)
        duration = self.timer.interval()
        with imageio.get_writer(location, format='mp4', mode='I', fps=1000/duration, quality=6) as writer:
            self.frame_no = 1
            for i in range(self.halfmax * 2 + 1):
                progress_box.setValue(i)
                if progress_box.wasCanceled():
                    remove(location)
                    return
                print(i)
                im_bytes = QByteArray()
                buf = QBuffer(im_bytes)
                buf.open(QIODevice.WriteOnly)
                self.grab().save(buf, 'PNG', 100)
                self.frame_no += 1
                writer.append_data(imageio.imread(im_bytes.data(), 'png'))
        progress_box.setValue(progress_box.maximum())

        msgbox = QMessageBox(QMessageBox.Information,
                             "Information",
                             "Export finished! Saved to {}".format(location))
        msgbox.exec()

    def paintEvent(self, *_):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)

        if self.draw_axes:
            painter.setPen(QPen(QColor(0, 0, 0, 64), 1))
            painter.drawLine(QLineF(0, self.height() / 2, 0, -self.height() / 2))
            painter.drawLine(QLineF(self.width() / 2, 0, -self.width() / 2, 0))

        colours = interpolate_hsv(self.col1, self.col2, self.num_dots - 2)
        last = None

        for cur_dot_num in range(self.num_dots):
            if self.join_end_dots:
                angle_off = radians(self.angle_factor/(self.num_dots-1)) * cur_dot_num
                frame_no = self.frame_no + cur_dot_num*(180/(self.num_dots-1))/self.speedmult
            else:
                angle_off = radians(self.angle_factor/self.num_dots) * cur_dot_num
                frame_no = self.frame_no + cur_dot_num*(180/self.num_dots)/self.speedmult
            colour = next(colours).toRgb()
            painter.setPen(QPen(colour))
            painter.setBrush(QBrush(colour))
            progress = abs((frame_no * self.speedmult) % (2*self.halfmax)-self.halfmax)
            height = sin(angle_off) * (self.height() - 100)
            width = cos(angle_off) * (self.width() - 100)
            x = cos(radians(self.x_multiplier * progress)) * width / 2
            y = cos(radians(self.y_multiplier * progress)) * height / 2

            if self.draw_lines:
                painter.setPen(QPen(colour, self.dot_size))
                painter.drawLine(QPointF(x, y), QPointF(0,0))
                if self.connect_lines:
                    if last:
                        painter.drawLine(QPointF(x, y), last)
                    last = QPointF(x,y)
            else:
                painter.drawEllipse(QPointF(x, y), self.dot_size, self.dot_size)


class Trigobox(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("Trigobox")
        self.setWindowFlags(Qt.Dialog)
        layout = QVBoxLayout(self)
        self.dotwid = DotsWidget()
        self.dotwid.timer = QTimer(self)
        self.dotwid.timer.timeout.connect(self.dotwid.next_animation_frame)
        layout.addWidget(self.dotwid)
        controls_box = QFormLayout()

        angle_factor_box = QHBoxLayout()
        self.angle_factor_slider = QSlider(Qt.Horizontal)
        self.angle_factor_slider.setMaximum(1080)
        self.angle_factor_slider.setValue(ANGLE_FACTOR_DEF)
        self.a_f_slider_val_label = QLabel(str(self.angle_factor_slider.value()))
        self.angle_factor_slider.valueChanged.connect(self.dotwid.change_angle_factor)
        angle_factor_box.addWidget(self.angle_factor_slider)
        angle_factor_box.addWidget(self.a_f_slider_val_label)
        controls_box.addRow("Angle", angle_factor_box)

        num_dots_box = QHBoxLayout()
        self.num_dots_slider = QSlider(Qt.Horizontal)
        self.num_dots_slider.setMinimum(2)
        self.num_dots_slider.setMaximum(300)
        self.num_dots_slider.setValue(NUM_DOTS_DEF)
        self.num_dots_slider.valueChanged.connect(self.dotwid.change_num_dots)
        self.num_dots_slider_val_label = QLabel(str(self.num_dots_slider.value()))
        num_dots_box.addWidget(self.num_dots_slider)
        num_dots_box.addWidget(self.num_dots_slider_val_label)
        controls_box.addRow("Number", num_dots_box)

        dot_size_box = QHBoxLayout()
        self.dot_size_slider = QSlider(Qt.Horizontal)
        self.dot_size_slider.setMinimum(1)
        self.dot_size_slider.setMaximum(40)
        self.dot_size_slider.setValue(DOT_SIZE_DEF)
        self.dot_size_slider.valueChanged.connect(self.dotwid.change_dot_size)
        self.dot_size_slider_val_label = QLabel(str(self.dot_size_slider.value()))
        dot_size_box.addWidget(self.dot_size_slider)
        dot_size_box.addWidget(self.dot_size_slider_val_label)
        controls_box.addRow("Thickness", dot_size_box)

        x_multiplier_box = QHBoxLayout()
        self.x_multiplier_slider = QSlider(Qt.Horizontal)
        self.x_multiplier_slider.setMaximum(10)
        self.x_multiplier_slider.setValue(X_MULT_DEF)
        self.x_multiplier_slider.valueChanged.connect(self.dotwid.change_x_multiplier)
        self.x_multiplier_slider_val_label = QLabel(str(self.x_multiplier_slider.value()))
        x_multiplier_box.addWidget(self.x_multiplier_slider)
        x_multiplier_box.addWidget(self.x_multiplier_slider_val_label)
        controls_box.addRow("X Multiplier", x_multiplier_box)

        y_multiplier_box = QHBoxLayout()
        self.y_multiplier_slider = QSlider(Qt.Horizontal)
        self.y_multiplier_slider.setMaximum(10)
        self.y_multiplier_slider.setValue(Y_MULT_DEF)
        self.y_multiplier_slider.valueChanged.connect(self.dotwid.change_y_multiplier)
        self.y_multiplier_slider_val_label = QLabel(str(self.y_multiplier_slider.value()))
        y_multiplier_box.addWidget(self.y_multiplier_slider)
        y_multiplier_box.addWidget(self.y_multiplier_slider_val_label)
        controls_box.addRow("Y Multiplier", y_multiplier_box)

        halfmax_box = QHBoxLayout()
        self.halfmax_slider = QSlider(Qt.Horizontal)
        self.halfmax_slider.setMinimum(1)
        self.halfmax_slider.setMaximum(720)
        self.halfmax_slider.setValue(HALFMAX_DEF)
        self.halfmax_slider.valueChanged.connect(self.dotwid.change_halfmax)
        self.halfmax_slider_val_label = QLabel(str(self.halfmax_slider.value()))
        halfmax_box.addWidget(self.halfmax_slider)
        halfmax_box.addWidget(self.halfmax_slider_val_label)
        controls_box.addRow("Period", halfmax_box)

        delay_box = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(0)
        self.delay_slider.setMaximum(100)
        self.delay_slider.setValue(DELAY_DEF)
        self.delay_slider.valueChanged.connect(self.change_delay)
        self.delay_slider_val_label = QLabel(str(self.delay_slider.value()))
        delay_box.addWidget(self.delay_slider)
        delay_box.addWidget(self.delay_slider_val_label)
        controls_box.addRow("Delay (ms)", delay_box)

        speedmult_box = QHBoxLayout()
        self.speedmult_slider = QSlider(Qt.Horizontal)
        self.speedmult_slider.setMaximum(12)
        self.speedmult_slider.setValue(SPEED_MULT_DEF)
        self.speedmult_slider.valueChanged.connect(self.dotwid.change_speedmult)
        self.speedmult_slider_val_label = QLabel(str(self.speedmult_slider.value()))
        speedmult_box.addWidget(self.speedmult_slider)
        speedmult_box.addWidget(self.speedmult_slider_val_label)
        controls_box.addRow("Speed", speedmult_box)

        self.draw_axes_checkbox = QCheckBox("Show axes")
        self.draw_axes_checkbox.setChecked(DRAW_AXES_DEF)
        self.draw_axes_checkbox.stateChanged.connect(self.dotwid.change_draw_axes)

        self.join_end_dots_checkbox = QCheckBox("Link first && last")
        self.draw_axes_checkbox.setChecked(JOIN_ENDS_DEF)
        self.join_end_dots_checkbox.stateChanged.connect(self.dotwid.change_join_end_dots)

        self.change_col1_button = QPushButton("")
        self.change_col1_button.setFlat(True)
        pal = QPalette()
        pal.setColor(QPalette.Button, COL1_DEF)
        self.change_col1_button.setPalette(pal)
        self.change_col1_button.setAutoFillBackground(True)
        self.change_col1_button.pressed.connect(self.change_col1)

        self.change_col2_button = QPushButton("")
        self.change_col2_button.setFlat(True)
        pal = QPalette()
        pal.setColor(QPalette.Button, COL2_DEF)
        self.change_col2_button.setPalette(pal)
        self.change_col2_button.setAutoFillBackground(True)
        self.change_col2_button.pressed.connect(self.change_col2)

        smaller_options_box = QHBoxLayout()
        smaller_options_box.addWidget(self.draw_axes_checkbox)
        smaller_options_box.addWidget(self.join_end_dots_checkbox)
        smaller_options_box.addStretch()
        smaller_options_box.addWidget(self.change_col1_button)
        smaller_options_box.addWidget(self.change_col2_button)
        controls_box.addRow(smaller_options_box)

        self.lines_checkbox = QCheckBox("Lines, not dots")
        self.lines_checkbox.setChecked(LINES_DEF)
        self.lines_checkbox.stateChanged.connect(self.dotwid.change_lines_state)

        self.connect_lines_checkbox = QCheckBox("Connect line ends")
        self.connect_lines_checkbox.setChecked(CONNECT_LINES_DEF)
        self.connect_lines_checkbox.setEnabled(LINES_DEF)
        self.connect_lines_checkbox.stateChanged.connect(self.dotwid.change_connect_lines)

        lines_options_box = QHBoxLayout()
        lines_options_box.addWidget(self.lines_checkbox)
        lines_options_box.addWidget(self.connect_lines_checkbox)
        lines_options_box.addStretch()
        controls_box.addRow(lines_options_box)

        reset_button = QPushButton("Reset values")
        reset_button.pressed.connect(self.reset_controls)

        export_button = QPushButton("Export a video")
        export_button.pressed.connect(self.dotwid.export_video)

        last_controls = QHBoxLayout()
        last_controls.addStretch()
        last_controls.addWidget(reset_button)
        last_controls.addStretch()
        last_controls.addWidget(export_button)
        controls_box.addRow(last_controls)

        controls_widget = QWidget(self)
        controls_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        pal = QPalette()
        pal.setColor(QPalette.Background, QColor("#fff"))
        controls_widget.setPalette(pal)
        controls_widget.setAutoFillBackground(True)
        controls_widget.setLayout(controls_box)

        layout.addWidget(controls_widget)
        self.dotwid.timer.start(DELAY_DEF)

        self.setWindowIcon(QIcon(resource_path("icon.png")))

    def change_delay(self, value):
        if not self.speedmult_slider.value() == 0:
            self.dotwid.timer.start(value)
        self.delay_slider_val_label.setText(str(value))

    def change_col1(self):
        colour = QColorDialog.getColor(self.dotwid.col1,
                                       self,
                                       "Choose a new primary colour")
        if not colour.isValid():
            return
        self.dotwid.col1 = colour
        pal = self.change_col1_button.palette()
        pal.setColor(QPalette.Button, colour)
        self.change_col1_button.setPalette(pal)
        if self.speedmult_slider.value() == 0:
            self.dotwid.frame_no -= 1
            self.dotwid.next_animation_frame()

    def change_col2(self):
        colour = QColorDialog.getColor(self.dotwid.col2,
                                       self,
                                       "Choose a new secondary colour")
        if not colour.isValid():
            return
        self.dotwid.col2 = colour
        pal = self.change_col2_button.palette()
        pal.setColor(QPalette.Button, colour)
        self.change_col2_button.setPalette(pal)
        if self.speedmult_slider.value() == 0:
            self.dotwid.frame_no -= 1
            self.dotwid.next_animation_frame()

    def reset_controls(self):

        self.delay_slider.setValue(DELAY_DEF)
        self.x_multiplier_slider.setValue(X_MULT_DEF)
        self.y_multiplier_slider.setValue(Y_MULT_DEF)
        self.dot_size_slider.setValue(DOT_SIZE_DEF)
        self.num_dots_slider.setValue(NUM_DOTS_DEF)
        self.angle_factor_slider.setValue(ANGLE_FACTOR_DEF)
        self.speedmult_slider.setValue(SPEED_MULT_DEF)
        self.halfmax_slider.setValue(HALFMAX_DEF)
        self.join_end_dots_checkbox.setChecked(JOIN_ENDS_DEF)
        self.draw_axes_checkbox.setChecked(DRAW_AXES_DEF)
        self.dotwid.col1 = COL1_DEF
        pal = self.change_col1_button.palette()
        pal.setColor(QPalette.Button, COL1_DEF)
        self.change_col1_button.setPalette(pal)
        self.dotwid.col2 = COL2_DEF
        pal = self.change_col2_button.palette()
        pal.setColor(QPalette.Button, COL2_DEF)
        self.change_col2_button.setPalette(pal)
        self.lines_checkbox.setChecked(LINES_DEF)
        self.connect_lines_checkbox.setChecked(LINES_DEF)
        self.connect_lines_checkbox.setEnabled(LINES_DEF)
        self.dotwid.frame_no = 1


def main():
    app = QApplication([])
    win = Trigobox()
    win.show()
    return app.exec()


if __name__ == '__main__':
    main()
