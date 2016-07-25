# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Graphical representation of a node on the QGraphicsScene.
"""

from ..qt import QtCore, QtGui, QtWidgets, QtSvg
from ..qt.qimage_svg_renderer import QImageSvgRenderer
from .note_item import NoteItem
from ..symbol import Symbol
from ..controller import Controller


import logging
log = logging.getLogger(__name__)


class NodeItem(QtSvg.QGraphicsSvgItem):

    """
    Node for the scene.

    :param node: Node instance
    """

    show_layer = False

    def __init__(self, node):
        super().__init__()

        # attached node
        self._node = node

        self._symbol = None

        # says if the attached node has been initialized
        # by the server.
        self._initialized = False

        # node label
        self._node_label = None

        # link items connected to this node item.
        self._links = []

        effect = QtWidgets.QGraphicsColorizeEffect()
        effect.setColor(QtGui.QColor("black"))
        effect.setStrength(0.8)
        self.setGraphicsEffect(effect)
        self.graphicsEffect().setEnabled(False)

        # set graphical settings for this node
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        # connect signals to know about some events
        # e.g. when the node has been started, stopped or suspended etc.
        node.created_signal.connect(self.createdSlot)
        node.started_signal.connect(self.startedSlot)
        node.stopped_signal.connect(self.stoppedSlot)
        node.suspended_signal.connect(self.suspendedSlot)
        node.updated_signal.connect(self.updatedSlot)
        node.deleted_signal.connect(self.deletedSlot)
        node.error_signal.connect(self.errorSlot)
        node.server_error_signal.connect(self.serverErrorSlot)

        # used when a port has been selected from the contextual menu
        self._selected_port = None

        # Use to detect the first time we display the label
        self._first_update_label = True

        # contains the last error message received
        # from the server.
        self._last_error = None

        from ..main_window import MainWindow
        self._main_window = MainWindow.instance()
        self._settings = self._main_window.uiGraphicsView.settings()

        if node.initialized():
            self.createdSlot(node.id())

    def _updateNode(self):
        """
        Sync change to the node
        """
        if self._initialized:
            self._node.setGraphics(self)

    def setSymbol(self, symbol):
        """
        :param symbol: Change the symbol path
        """
        # create renderer using symbols path/resource
        if symbol is None:
            symbol = self._node.defaultSymbol()
        if self._symbol != symbol:
            self._symbol = symbol

            # Temporary symbol during loading
            renderer = QImageSvgRenderer(":/icons/reload.svg")
            renderer.setObjectName("symbol_loading")
            self.setSharedRenderer(renderer)

            Controller.instance().getStatic(Symbol(symbol_id=symbol).url(), self._symbolLoadedCallback)

    def symbol(self):
        return self._symbol

    def _symbolLoadedCallback(self, path):
        renderer = QImageSvgRenderer(path)
        renderer.setObjectName(path)
        self.setSharedRenderer(renderer)
        if self._node.settings().get("symbol") != self._symbol:
            self._updateNode()
        if not self._initialized:
            self._showLabel()
            self._initialized = True
            if self._node.creator():
                self._updateNode()

    def node(self):
        """
        Returns the node attached to this node item.

        :returns: Node instance
        """

        return self._node

    def setPos(self, *args):
        super().setPos(*args)
        self._node.setSettingValue("x", int(self.x()))
        self._node.setSettingValue("y", int(self.y()))

    def addLink(self, link):
        """
        Adds a link items to this node item.

        :param link: LinkItem instance
        """

        self._links.append(link)
        self._node.updated_signal.emit()

    def removeLink(self, link):
        """
        Removes a link items from this node item.

        :param link: LinkItem instance
        """

        if link in self._links:
            self._links.remove(link)

    def links(self):
        """
        Returns all the link items attached to this node item.

        :returns: list of LinkItem instances
        """

        return self._links

    def createdSlot(self, base_node_id):
        """
        Slot to receive events from the attached Node instance
        when a the node has been created/initialized.

        :param base_node_id: base node identifier (integer)
        """

        if self is None:
            return
        self.setPos(QtCore.QPoint(self._node.x(), self._node.y()))
        self.setSymbol(self._node.symbol())
        self.update()

    def startedSlot(self):
        """
        Slot to receive events from the attached Node instance
        when a the node has started.
        """

        if self is None:
            return
        for link in self._links:
            link.update()

    def stoppedSlot(self):
        """
        Slot to receive events from the attached Node instance
        when a the node has stopped.
        """

        if self is None:
            return
        for link in self._links:
            link.update()

    def suspendedSlot(self):
        """
        Slot to receive events from the attached Node instance
        when a the node has suspended.
        """

        if self is None:
            return
        for link in self._links:
            link.update()

    def updatedSlot(self):
        """
        Slot to receive events from the attached Node instance
        when a the node has been updated.
        """

        if self is None:
            return

        self.setSymbol(self._node.settings().get("symbol"))
        self.setPos(self._node.settings().get("x", 0), self._node.settings().get("y", 0))
        self.setZValue(self._node.settings().get("z", 0))

        self._updateLabel()

        # update the link tooltips in case the
        # node name has changed
        for link in self._links:
            link.setCustomToolTip()

    def deletedSlot(self):
        """
        Slot to receive events from the attached Node instance
        when the node has been deleted.
        """

        if self is None or not self.scene():
            return
        if self in self.scene().items():
            self.scene().removeItem(self)

    def serverErrorSlot(self, base_node_id, message):
        """
        Slot to receive events from the attached Node instance
        when the node has received an error from the server.

        :param base_node_id: base node identifier
        :param message: error message
        """

        if self:
            self._last_error = "{message}".format(message=message)

    def errorSlot(self, base_node_id, message):
        """
        Slot to receive events from the attached Node instance
        when the node wants to report an error.

        :param base_node_id: base node identifier
        :param message: error message
        """

        if self:
            self._last_error = "{message}".format(message=message)

    def setCustomToolTip(self):
        """
        Sets a new ToolTip.
        """

        if not self._initialized:
            if not self._last_error:
                error = "unknown error"
            else:
                error = self._last_error
            self.setToolTip("This node isn't initialized\n{}".format(error))
        else:
            self.setToolTip(self._node.info())

    def label(self):
        """
        Returns the node label.

        :return: NoteItem instance.
        """

        return self._node_label

    def _labelUnselectedSlot(self):
        """
        Called when user unselect the label
        """
        self._updateNode()

    def _centerLabel(self):
        """
        Centers the node label.
        """

        text_rect = self._node_label.boundingRect()
        text_middle = text_rect.topRight() / 2
        node_rect = self.boundingRect()
        node_middle = node_rect.topRight() / 2
        label_x_pos = node_middle.x() - text_middle.x()
        label_y_pos = -25
        self._node_label.setPos(label_x_pos, label_y_pos)

    def _showLabel(self):
        """
        Shows the node label on the scene.
        """

        if not self._node_label:
            self._node_label = NoteItem(self)
            self._node_label.item_unselected_signal.connect(self._labelUnselectedSlot)
            self._node_label.setEditable(False)
            self._updateLabel()
            self._node.setSettingValue("label", self._node_label.dump())

    def _updateLabel(self):
        """
        Update the label using the informations stored in the node
        """
        if not self._node_label:
            return
        self._node_label.setPlainText(self._node.name())
        label_data = self._node.settings().get("label")

        if self._node.creator() and self._first_update_label:
            self._centerLabel()
        elif label_data:
            if self._node_label.toPlainText() != self._node.name():
                self._node_label.setPlainText(self._node.name())
            self._node_label.setPos(label_data["x"], label_data["y"])
            self._node_label.setStyle(label_data["style"])
            self._node_label.setRotation(label_data["rotation"])
        self._first_update_label = False

    def connectToPort(self, unavailable_ports=[]):
        """
        Shows a contextual menu for the user to choose port or auto-select one.

        :param unavailable_ports: list of port names that the user cannot choose

        :returns: Port instance corresponding to the selected port
        """

        self._selected_port = None
        menu = QtWidgets.QMenu()
        ports = self._node.ports()
        if not ports:
            QtWidgets.QMessageBox.critical(self.scene().parent(), "Link", "No port available, please configure this device")
            return None

        # sort the ports
        ports_dict = {}
        for port in ports:
            if port.adapterNumber() is not None:
                # make the port number unique (special case with WICs).
                port_number = port.portNumber()
                if port_number >= 16:
                    port_number *= 8
                ports_dict[(port.adapterNumber() * 16) + port_number] = port
            elif port.portNumber()is not None:
                ports_dict[port.portNumber()] = port
            else:
                ports_dict[port.name()] = port

        try:
            ports = sorted(ports_dict.keys(), key=int)
        except ValueError:
            ports = sorted(ports_dict.keys())

        # show a contextual menu for the user to choose a port
        for port in ports:
            port_object = ports_dict[port]
            log.debug("Node '{}' Port {} Type {}".format(self.node(), port_object.name(), type(port_object.name())))
            if port in unavailable_ports:
                # this port cannot be chosen by the user (grayed out)
                action = menu.addAction(QtGui.QIcon(':/icons/led_green.svg'), port_object.name())
                action.setDisabled(True)
            elif port_object.isFree():
                menu.addAction(QtGui.QIcon(':/icons/led_red.svg'), port_object.name())
            else:
                menu.addAction(QtGui.QIcon(':/icons/led_green.svg'), port_object.name())

        menu.triggered.connect(self.selectedPortSlot)
        menu.exec_(QtGui.QCursor.pos())
        return self._selected_port

    def selectedPortSlot(self, action):
        """
        Slot to receive events when a port has been selected in the
        contextual menu.

        :param action: QAction instance
        """

        ports = self._node.ports()

        # get the Port instance based on the selected port name.
        for port in ports:
            if port.name() == str(action.text()):
                self._selected_port = port
                break

    def itemChange(self, change, value):
        """
        Notifies this node item that some part of the item's state changes.

        :param change: GraphicsItemChange type
        :param value: value of the change
        """

        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged and self.isActive() and self._main_window.uiSnapToGridAction.isChecked():
            GRID_SIZE = 75
            mid_x = self.boundingRect().width() / 2
            tmp_x = (GRID_SIZE * round((self.x() + mid_x) / GRID_SIZE)) - mid_x
            mid_y = self.boundingRect().height() / 2
            tmp_y = (GRID_SIZE * round((self.y() + mid_y) / GRID_SIZE)) - mid_y
            if tmp_x != self.x() and tmp_y != self.y():
                self.setPos(tmp_x, tmp_y)

        # dynamically change the renderer when this node item is selected/unselected.
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange:
            if value:
                self.graphicsEffect().setEnabled(True)
            else:
                self.graphicsEffect().setEnabled(False)
                self._updateNode()

        # adjust link item positions when this node is moving or has changed.
        if change == QtWidgets.QGraphicsItem.ItemPositionChange or change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for link in self._links:
                link.adjust()

        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """
        Paints the contents of an item in local coordinates.

        :param painter: QPainter instance
        :param option: QStyleOptionGraphicsItem instance
        :param widget: QWidget instance
        """

        # don't show the selection rectangle
        if not self._settings["draw_rectangle_selected_item"]:
            option.state = QtWidgets.QStyle.State_None
        super().paint(painter, option, widget)

        if not self._initialized or self.show_layer:
            brect = self.boundingRect()
            center = self.mapFromItem(self, brect.width() / 2.0, brect.height() / 2.0)
            painter.setBrush(QtCore.Qt.red)
            painter.setPen(QtCore.Qt.red)
            painter.drawRect((brect.width() / 2.0) - 10, (brect.height() / 2.0) - 10, 20, 20)
            painter.setPen(QtCore.Qt.black)
            if self.show_layer:
                text = str(int(self.zValue()))  # Z value
            elif self._last_error:
                text = "E"  # error
            else:
                text = "S"  # initialization
            painter.drawText(QtCore.QPointF(center.x() - 4, center.y() + 4), text)

    def setZValue(self, value):
        """
        Sets a new Z value.

        :param value: Z value
        """

        super().setZValue(value)
        if self.zValue() < 0:
            self.setFlag(self.ItemIsSelectable, False)
            self.setFlag(self.ItemIsMovable, False)
            if self._node_label:
                self._node_label.setFlag(self.ItemIsSelectable, False)
                self._node_label.setFlag(self.ItemIsMovable, False)
        else:
            self.setFlag(self.ItemIsSelectable, True)
            self.setFlag(self.ItemIsMovable, True)
            if self._node_label:
                self._node_label.setFlag(self.ItemIsSelectable, True)
                self._node_label.setFlag(self.ItemIsMovable, True)
        for link in self._links:
            link.adjust()
        self._node.setSettingValue("z", int(value))

    def hoverEnterEvent(self, event):
        """
        Handles all hover enter events for this item.

        :param event: QGraphicsSceneHoverEvent instance
        """

        self.setCustomToolTip()
        if not self.isSelected():
            self.graphicsEffect().setEnabled(True)

    def hoverLeaveEvent(self, event):
        """
        Handles all hover leave events for this item.

        :param event: QGraphicsSceneHoverEvent instance
        """

        if not self.isSelected():
            self.graphicsEffect().setEnabled(False)

