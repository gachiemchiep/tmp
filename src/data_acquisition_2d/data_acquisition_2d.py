#!/usr/bin/env python

from __future__ import division
import os
import rospkg
import rospy

from python_qt_binding import loadUi
from python_qt_binding.QtCore import QAbstractListModel, QFile, QIODevice, Qt, Signal, QSize, QRectF
from python_qt_binding.QtGui import QIcon, QImage, QPainter, QPixmap
from python_qt_binding.QtWidgets import QCompleter, QFileDialog, QGraphicsScene, QWidget
from python_qt_binding.QtSvg import QSvgGenerator

import rosgraph.impl.graph
import rosservice
import rostopic
import cv2
import numpy as np

from enum import Enum
from qt_dotgraph.dot_to_qt import DotToQtGenerator
from sensor_msgs.msg import Image
# pydot requires some hacks
from qt_dotgraph.pydotfactory import PydotFactory
from rqt_gui_py.plugin import Plugin
# TODO: use pygraphviz instead, but non-deterministic layout will first be resolved in graphviz 2.30
# from qtgui_plugin.pygraphvizfactory import PygraphvizFactory


from .dotcode import RosGraphDotcodeGenerator, NODE_NODE_GRAPH, NODE_TOPIC_ALL_GRAPH, NODE_TOPIC_GRAPH
from .interactive_graphics_view import InteractiveGraphicsView

try:
    unicode
    # we're on python2, or the "unicode" function has already been defined elsewhere
except NameError:
    unicode = str
    # we're on python3

from libs.canvas import Canvas

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(30,30,600,400)
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.show()

    def paintEvent(self, event):
        qp = QPainter(self)
        br = QBrush(QColor(100, 10, 10, 40))
        qp.setBrush(br)
        qp.drawRect(QtCore.QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.update()

class DataAcquisition(Plugin):

    _deferred_fit_in_view = Signal()

    def __init__(self, context):
        super(DataAcquisition, self).__init__(context)
        self.initialized = False
        self.setObjectName('DataAcquisition')

        self._graph = None
        self._current_dotcode = None

        self._widget = QWidget()

        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('data_acquisition_2d'), 'resource', 'data_acquisition.ui')
        loadUi(ui_file, self._widget, {'InteractiveGraphicsView': InteractiveGraphicsView})
        self._widget.setObjectName('DataAcquisitionUi')
        if context.serial_number() > 1:
            self._widget.setWindowTitle(
                self._widget.windowTitle() + (' (%d)' % context.serial_number()))

        # Fixed size
        width = 670
        height = 570
        # setting  the fixed size of window 
        self._widget.setFixedSize(width, height)

        # Get a list of Image topic
        self._get_image_topics()

        # Robot mode : disable GUI when scanning 
        self._in_scanning = False
        self._scan_time = 0
        self._image_topic = None

        # canvas : image will be load here
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(Qt.red)
        self._scene.setSceneRect( 0, 0, 640, 480 )
        self._widget.canvas.setScene(self._scene)
        self._set_image()


        # Button Event
        self._widget.setup_robot_push_button.pressed.connect(self._setup_robot)
        self._widget.save_ground_truth_push_button.pressed.connect(self._save_ground_truth)
        self._widget.create_bbox_push_button.pressed.connect(self._create_bbox)
        self._widget.start_scanning_push_button.pressed.connect(self._start_scanning)

        # Box event
        self._widget.scan_time_spin_box.valueChanged.connect(self._set_scan_time)
        self._widget.image_topic_combo_box.currentIndexChanged.connect(self._set_image_topic)


        context.add_widget(self._widget)


    def _setup_robot(self):
        print("_setup_robot")

    def _save_ground_truth(self):
        print("_save_ground_truth")

    def _create_bbox(self):
        print("_create_bbox for image from topic : {} ".format(self._widget.image_topic_combo_box.itemData(
            self._widget.image_topic_combo_box.currentIndex())))

    def _start_scanning(self):
        print("_start_scanning")

    def _set_scan_time(self):
        if not self._in_scanning:
            self._scan_time = self._widget.scan_time_spin_box.value()
            print("_set_scan_time : {}".format(self._widget.scan_time_spin_box.value()))
        else:
            print("Is scanning. Can't set the value")

    def _get_image_topics(self):

        topic_list = rospy.get_published_topics()
        index = 0
        for topic in topic_list:
            # Remove topic which doesn't contain Image from list
            try:
                msg = rospy.wait_for_message(topic, Image, timeout=0.1)
                self._widget.image_topic_combo_box.insertItem(index, self.tr(topic), topic)
                index = index + 1
            except Exception as err:
                continue

        self._widget.image_topic_combo_box.insertItem(0, self.tr("aaaaa"), "aaaaa")
        self._widget.image_topic_combo_box.insertItem(1, self.tr("bbbbb"), "bbbbb")
        self._widget.image_topic_combo_box.setCurrentIndex(0)


    def _set_image_topic(self):
        print(self._widget.image_topic_combo_box.currentIndex())
        print(self._widget.image_topic_combo_box.itemData(
            self._widget.image_topic_combo_box.curre_current_dotcodentIndex()))
        print("_set_image_topic : {}".format(self._image_topic))

        self._set_image()

    def _set_image(self):
        print("_set_image")
        self._scene.clear()
        img = cv2.imread("/home/gachiemchiep/Pictures/aaa.png", 1)
        img_rz = cv2.resize(img, (640, 480))

        # https://stackoverflow.com/questions/34232632/convert-python-opencv-image-numpy-array-to-pyqt-qpixmap-image
        height, width, channel = img_rz.shape
        print(img_rz.shape)
        bytesPerLine = 3 * width
        img_q = QImage(img_rz.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()

        # painter : this does not work
        # painter = QPainter(img_q)
        # painter.setRenderHint(QPainter.Antialiasing)
        # self._scene.render(painter)
        # painter.end()

        # pixmap : this work
        pixmap = QPixmap.fromImage(img_q)
        self._scene.addPixmap(pixmap)

        self._scene.setSceneRect( 0, 0, 640, 480)

    def _draw_bbox_start(self, event):
        print("_draw_bbox_start: {}".format(event.pos()))

    def _draw_bbox_end(self, event):
        print("_draw_bbox_end: {}".format(event.pos()))

