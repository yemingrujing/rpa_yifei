import sys
import json
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QDockWidget, QListWidget,
    QTextEdit, QPushButton, QLabel, QSplitter, QFileDialog, QMessageBox,
    QProgressBar, QTreeWidget, QTreeWidgetItem, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QRadioButton, QLineEdit, QGroupBox,
    QScrollArea, QFrame, QSizePolicy, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox, QFormLayout,
    QColorDialog, QFontDialog, QInputDialog, QCalendarWidget, QLayout, QLayoutItem,
    QGraphicsView, QGraphicsScene, QGraphicsPathItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QRect, QPoint, pyqtSignal, QMimeData, QByteArray,
    QDataStream, QBuffer, QIODevice, QSettings, QTranslator, QLocale,
    QSizeF, QPointF, QRectF, QThread, pyqtSlot, QEvent, QObject
)
from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QImage, QBrush, QPen, QPainter, QColor,
    QFont, QKeySequence, QCursor, QDrag, QDropEvent, QDragEnterEvent,
    QDragLeaveEvent, QMouseEvent, QPaintEvent, QResizeEvent, QCloseEvent,
    QFocusEvent, QKeyEvent, QWheelEvent, QContextMenuEvent, QPainterPath,
    QLinearGradient
)
import traceback


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        self._hSpacing = hSpacing
        self._vSpacing = vSpacing
        self._items = []
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
    
    def __del__(self):
        while self.count():
            self.takeAt(0)
    
    def addItem(self, item):
        self._items.append(item)
    
    def count(self):
        return len(self._items)
    
    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), True)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size
    
    def _doLayout(self, rect, testOnly=False):
        margins = self.contentsMargins()
        left = margins.left()
        top = margins.top()
        right = margins.right()
        bottom = margins.bottom()
        effectiveRect = rect.adjusted(left, top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0
        
        hSpace = self._hSpacing
        vSpace = self._vSpacing
        
        if hSpace < 0:
            hSpace = self.spacing()
        if vSpace < 0:
            vSpace = self.spacing()
        
        for item in self._items:
            wid = item.widget()
            spaceX = hSpace
            spaceY = vSpace
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        
        return y + lineHeight - rect.y() + bottom


class ComponentLibrary:
    COMPONENTS = {
        '输入': [
            {'id': 'input_text', 'name': '输入文本', 'category': '输入', 'icon': '⌨️'},
            {'id': 'input_variable', 'name': '设置变量', 'category': '输入', 'icon': '📦'},
            {'id': 'input_dialog', 'name': '对话框输入', 'category': '输入', 'icon': '💬'},
        ],
        '输出': [
            {'id': 'output_message', 'name': '消息框', 'category': '输出', 'icon': '📢'},
            {'id': 'output_log', 'name': '输出日志', 'category': '输出', 'icon': '📝'},
            {'id': 'output_variable', 'name': '获取变量', 'category': '输出', 'icon': '🔍'},
        ],
        '鼠标': [
            {'id': 'mouse_click', 'name': '鼠标点击', 'category': '鼠标', 'icon': '🖱️'},
            {'id': 'mouse_move', 'name': '移动鼠标', 'category': '鼠标', 'icon': '👆'},
            {'id': 'mouse_drag', 'name': '拖拽', 'category': '鼠标', 'icon': '✋'},
            {'id': 'mouse_scroll', 'name': '滚动', 'category': '鼠标', 'icon': '📜'},
        ],
        '键盘': [
            {'id': 'keyboard_type', 'name': '输入文本', 'category': '键盘', 'icon': '⌨️'},
            {'id': 'keyboard_press', 'name': '按键', 'category': '键盘', 'icon': '🔘'},
            {'id': 'keyboard_hotkey', 'name': '快捷键', 'category': '键盘', 'icon': '⚡'},
        ],
        '等待': [
            {'id': 'wait_seconds', 'name': '等待秒数', 'category': '等待', 'icon': '⏱️'},
            {'id': 'wait_image', 'name': '等待图像', 'category': '等待', 'icon': '🖼️'},
            {'id': 'wait_window', 'name': '等待窗口', 'category': '等待', 'icon': '🪟'},
        ],
        '流程控制': [
            {'id': 'condition_if', 'name': '如果', 'category': '流程控制', 'icon': '🔀'},
            {'id': 'condition_else', 'name': '否则', 'category': '流程控制', 'icon': '🔀'},
            {'id': 'loop_while', 'name': '循环', 'category': '流程控制', 'icon': '🔁'},
            {'id': 'loop_for', 'name': 'For循环', 'category': '流程控制', 'icon': '🔂'},
            {'id': 'try_catch', 'name': '尝试捕获', 'category': '流程控制', 'icon': '🛡️'},
            {'id': 'flow_break', 'name': '中断', 'category': '流程控制', 'icon': '⏹️'},
            {'id': 'flow_continue', 'name': '继续', 'category': '流程控制', 'icon': '⏩'},
        ],
        '数据处理': [
            {'id': 'excel_read', 'name': '读取Excel', 'category': '数据处理', 'icon': '📊'},
            {'id': 'excel_write', 'name': '写入Excel', 'category': '数据处理', 'icon': '📝'},
            {'id': 'excel_append', 'name': '追加Excel', 'category': '数据处理', 'icon': '➕'},
            {'id': 'data_filter', 'name': '筛选数据', 'category': '数据处理', 'icon': '🔍'},
            {'id': 'data_transform', 'name': '转换数据', 'category': '数据处理', 'icon': '🔄'},
        ],
        '文件操作': [
            {'id': 'file_read', 'name': '读取文件', 'category': '文件操作', 'icon': '📄'},
            {'id': 'file_write', 'name': '写入文件', 'category': '文件操作', 'icon': '✍️'},
            {'id': 'file_copy', 'name': '复制文件', 'category': '文件操作', 'icon': '📋'},
            {'id': 'file_delete', 'name': '删除文件', 'category': '文件操作', 'icon': '🗑️'},
            {'id': 'file_list', 'name': '列出文件', 'category': '文件操作', 'icon': '📁'},
        ],
        '通信': [
            {'id': 'email_send', 'name': '发送邮件', 'category': '通信', 'icon': '📧'},
            {'id': 'email_receive', 'name': '接收邮件', 'category': '通信', 'icon': '📬'},
            {'id': 'api_request', 'name': 'API请求', 'category': '通信', 'icon': '🌐'},
        ],
        '集成': [
            {'id': 'db_query', 'name': '数据库查询', 'category': '集成', 'icon': '🗄️'},
            {'id': 'db_execute', 'name': '执行SQL', 'category': '集成', 'icon': '⚙️'},
        ],
        '浏览器': [
            {'id': 'web_open', 'name': '打开网页', 'category': '浏览器', 'icon': '🌐'},
            {'id': 'web_click', 'name': '点击元素', 'category': '浏览器', 'icon': '🖱️'},
            {'id': 'web_input', 'name': '输入文本', 'category': '浏览器', 'icon': '⌨️'},
            {'id': 'web_get_text', 'name': '获取文本', 'category': '浏览器', 'icon': '📝'},
            {'id': 'web_get_attr', 'name': '获取属性', 'category': '浏览器', 'icon': '📋'},
            {'id': 'web_screenshot', 'name': '网页截图', 'category': '浏览器', 'icon': '📸'},
            {'id': 'web_close', 'name': '关闭浏览器', 'category': '浏览器', 'icon': '❌'},
        ],
    }


class ComponentItemWidget(QFrame):
    clicked = pyqtSignal(str)
    
    def __init__(self, component_data, parent=None):
        super().__init__(parent)
        self.component_data = component_data
        self.setFixedWidth(90)
        self.setMinimumHeight(50)
        self.setMaximumHeight(70)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
            }
            QFrame:hover {
                border: 2px solid #0078d4;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        icon_label = QLabel(component_data.get('icon', '📦'))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 18px;")
        
        name_label = QLabel(component_data.get('name', ''))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-size: 9px; color: #333;")
        
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addStretch()
    
    def sizeHint(self):
        return QSize(90, 60)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if hasattr(self, '_drag_start_pos'):
                diff = event.pos() - self._drag_start_pos
                if diff.manhattanLength() > 5:
                    drag = QDrag(self)
                    mime_data = QMimeData()
                    mime_data.setText(self.component_data['id'])
                    drag.setMimeData(mime_data)
                    
                    pixmap = self.grab()
                    drag.setPixmap(pixmap)
                    drag.setHotSpot(pixmap.rect().center())
                    
                    drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.component_data['id'])
        super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        self.setStyleSheet("background-color: #e0e0e0; border: 2px solid #0078d4;")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.setStyleSheet("background-color: white; border: 1px solid #cccccc;")
        super().leaveEvent(event)


class FlowNodeWidget(QFrame):
    selected = pyqtSignal(str)
    moved = pyqtSignal(str, int, int)
    connection_requested = pyqtSignal(str)
    port_clicked = pyqtSignal(str, str)
    
    def __init__(self, node_id, title, node_type='action', parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.title = title
        self.node_type = node_type
        self.connected = False
        
        self.setFixedSize(150, 80)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        
        self._setup_ui()
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        type_label = QLabel(f"类型: {self.node_type}")
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet("font-size: 9px; color: gray;")
        
        main_layout.addWidget(title_label)
        main_layout.addWidget(type_label)
        
        colors = {
            'action': '#4CAF50',
            'condition': '#FF9800',
            'loop': '#2196F3',
            'try': '#9C27B0',
            'start': '#00BCD4',
            'end': '#F44336',
            'browser': '#E91E63'
        }
        border_color = colors.get(self.node_type, '#9E9E9E')
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {border_color};
                border-radius: 5px;
            }}
        """)
    
    def get_output_port_pos(self):
        return self.x() + self.width() // 2, self.y() + self.height()
    
    def get_input_port_pos(self):
        return self.x() + self.width() // 2, self.y()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.node_id)
            self.drag_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            diff = event.pos() - self.drag_position
            new_pos = self.pos() + diff
            self.move(new_pos)
            self.moved.emit(self.node_id, new_pos.x(), new_pos.y())
        super().mouseMoveEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.connection_requested.emit(self.node_id)
        super().mouseDoubleClickEvent(event)


class FlowDesignerWidget(QWidget):
    node_selected = pyqtSignal(str)
    node_moved = pyqtSignal(str, int, int)
    canvas_modified = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = {}
        self.connections = []
        self.selected_node = None
        self.connecting_from = None
        self.temp_connection_start = None
        self.temp_connection_end = None
        self.is_connecting = False
        self.hovered_connection = None
        self.dragging_control_point = None
        self.control_points = {}
        
        self.setAcceptDrops(True)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #f5f5f5; border: 1px solid #cccccc;")
        self.setMouseTracking(True)
        
        self.grid_size = 20
        self.show_grid = True
        
        self.start_node_id = None
        self.end_node_id = None
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        component_id = event.mimeData().text()
        pos = event.position().toPoint()
        
        self.add_node(component_id, pos.x(), pos.y())
        event.acceptProposedAction()
    
    def add_node(self, component_id, x, y):
        node_id = f"node_{len(self.nodes) + 1}"
        title = self._get_component_title(component_id)
        node_type = self._get_component_type(component_id)
        
        node = FlowNodeWidget(node_id, title, node_type, self)
        node.move(x, y)
        node.show()
        
        node.selected.connect(self._on_node_selected)
        node.moved.connect(self._on_node_moved)
        
        self.nodes[node_id] = {
            'widget': node,
            'component_id': component_id,
            'x': x,
            'y': y,
            'connections': [],
            'properties': {}
        }
        
        self.canvas_modified.emit()
        return node_id
    
    def _get_component_title(self, component_id):
        for category, components in ComponentLibrary.COMPONENTS.items():
            for comp in components:
                if comp['id'] == component_id:
                    return comp['name']
        return component_id
    
    def _get_component_type(self, component_id):
        type_mapping = {
            'condition_if': 'condition',
            'condition_else': 'condition',
            'loop_while': 'loop',
            'loop_for': 'loop',
            'try_catch': 'try',
            'flow_break': 'action',
            'flow_continue': 'action',
        }
        return type_mapping.get(component_id, 'action')
    
    def _on_node_selected(self, node_id):
        self.node_selected.emit(node_id)
        self.selected_node = node_id
        
        for nid, node_data in self.nodes.items():
            if nid == node_id:
                node_data['widget'].setStyleSheet(node_data['widget'].styleSheet() + "border: 3px solid #0078d4;")
            else:
                original_style = node_data['widget'].styleSheet()
                node_data['widget'].setStyleSheet(original_style.replace("border: 3px solid #0078d4;", "border: 2px solid;"))
    
    def _on_node_moved(self, node_id, x, y):
        if node_id in self.nodes:
            self.nodes[node_id]['x'] = x
            self.nodes[node_id]['y'] = y
            
            keys_to_remove = [k for k in self.control_points.keys() 
                            if k.startswith(f"{node_id}->") or f"->{node_id}" in k]
            for key in keys_to_remove:
                del self.control_points[key]
        
        self.update()
        self.canvas_modified.emit()
    
    def remove_node(self, node_id):
        if node_id in self.nodes:
            self.nodes[node_id]['widget'].close()
            del self.nodes[node_id]
            self.canvas_modified.emit()
    
    def clear_all(self):
        for node_id in list(self.nodes.keys()):
            self.remove_node(node_id)
        self.connections.clear()
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        
        for conn in self.connections:
            start_node_id = conn['from']
            end_node_id = conn['to']
            
            if start_node_id in self.nodes and end_node_id in self.nodes:
                start_widget = self.nodes[start_node_id]['widget']
                end_widget = self.nodes[end_node_id]['widget']
                
                start_pos = start_widget.get_output_port_pos()
                end_pos = end_widget.get_input_port_pos()
                
                is_hovered = (self.hovered_connection == conn)
                conn_key = f"{start_node_id}->{end_node_id}"
                
                self._draw_connection_line(painter, start_pos, end_pos, is_hovered, conn_key)
        
        if self.is_connecting and self.temp_connection_start and self.temp_connection_end:
            pen = QPen(QColor('#0078D4'), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            self._draw_connection_line(painter, self.temp_connection_start, self.temp_connection_end, False, None)
        
        self._draw_port_indicators(painter)
        self._draw_control_points(painter)
    
    def _get_control_point(self, conn_key, start_pos, end_pos):
        if conn_key not in self.control_points:
            if isinstance(start_pos, QPoint):
                sx, sy = start_pos.x(), start_pos.y()
            else:
                sx, sy = start_pos[0], start_pos[1]
            if isinstance(end_pos, QPoint):
                ex, ey = end_pos.x(), end_pos.y()
            else:
                ex, ey = end_pos[0], end_pos[1]
            
            cx = (sx + ex) / 2
            cy = (sy + ey) / 2
            self.control_points[conn_key] = QPoint(int(cx), int(cy))
        
        return self.control_points[conn_key]
    
    def _draw_connection_line(self, painter, start, end, is_hovered=False, conn_key=None):
        if isinstance(start, QPoint):
            start_x, start_y = start.x(), start.y()
        else:
            start_x, start_y = start[0], start[1]
        
        if isinstance(end, QPoint):
            end_x, end_y = end.x(), end.y()
        else:
            end_x, end_y = end[0], end[1]
        
        control_point = self._get_control_point(conn_key, start, end) if conn_key else None
        
        path = QPainterPath()
        path.moveTo(start_x, start_y)
        
        if control_point:
            cp_x, cp_y = control_point.x(), control_point.y()
        else:
            distance = abs(end_y - start_y)
            control_offset = max(distance * 0.4, 50)
            cp_x = (start_x + end_x) / 2
            cp_y = start_y + control_offset
        
        path.quadTo(cp_x, cp_y, end_x, end_y)
        
        if is_hovered:
            pen = QPen(QColor('#FF6B6B'), 4)
            arrow_color = QColor('#FF6B6B')
        else:
            pen = QPen(QColor('#0078D4'), 2)
            arrow_color = QColor('#0078D4')
        
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        
        glow_pen = QPen(QColor(arrow_color.red(), arrow_color.green(), arrow_color.blue(), 50), 8)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        painter.drawPath(path)
        
        if control_point:
            arrow_size = 10
            angle = math.atan2(end_y - cp_y, end_x - cp_x)
            
            arrow_p1_x = end_x - arrow_size * math.cos(angle - math.pi / 6)
            arrow_p1_y = end_y - arrow_size * math.sin(angle - math.pi / 6)
            arrow_p2_x = end_x - arrow_size * math.cos(angle + math.pi / 6)
            arrow_p2_y = end_y - arrow_size * math.sin(angle + math.pi / 6)
            
            arrow_path = QPainterPath()
            arrow_path.moveTo(end_x, end_y)
            arrow_path.lineTo(arrow_p1_x, arrow_p1_y)
            arrow_path.lineTo(arrow_p2_x, arrow_p2_y)
            arrow_path.closeSubpath()
            
            painter.fillPath(arrow_path, QBrush(arrow_color))
    
    def _draw_control_points(self, painter):
        for conn_key, control_point in self.control_points.items():
            is_dragging = (self.dragging_control_point == conn_key)
            
            if is_dragging:
                painter.setPen(QPen(QColor('#FF6B6B'), 2))
                painter.setBrush(QBrush(QColor('#FF6B6B')))
                painter.drawEllipse(control_point, 8, 8)
                
                glow_color = QColor('#FF6B6B')
                glow_color.setAlpha(100)
                glow_pen = QPen(glow_color, 16)
                glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(glow_pen)
                painter.setBrush(QBrush())
                painter.drawEllipse(control_point, 8, 8)
            else:
                painter.setPen(QPen(QColor('#0078D4'), 2))
                painter.setBrush(QBrush(QColor('#FFFFFF')))
                painter.drawEllipse(control_point, 6, 6)
    
    def _draw_port_indicators(self, painter):
        for node_id, node_data in self.nodes.items():
            widget = node_data['widget']
            
            input_pos = widget.get_input_port_pos()
            output_pos = widget.get_output_port_pos()
            
            if isinstance(input_pos, tuple):
                input_x, input_y = input_pos
            else:
                input_x, input_y = input_pos.x(), input_pos.y()
            
            if isinstance(output_pos, tuple):
                output_x, output_y = output_pos
            else:
                output_x, output_y = output_pos.x(), output_pos.y()
            
            painter.setPen(QPen(QColor('#0078D4'), 2))
            painter.setBrush(QBrush(QColor('#FFFFFF')))
            painter.drawEllipse(int(input_x), int(input_y), 12, 12)
            
            painter.setPen(QPen(QColor('#28A745'), 2))
            painter.setBrush(QBrush(QColor('#FFFFFF')))
            painter.drawEllipse(int(output_x), int(output_y), 12, 12)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            for conn_key, control_point in self.control_points.items():
                if (event.pos() - control_point).manhattanLength() < 15:
                    self.dragging_control_point = conn_key
                    self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
                    return
            
            for node_id, node_data in self.nodes.items():
                widget = node_data['widget']
                input_pos = widget.get_input_port_pos()
                output_pos = widget.get_output_port_pos()
                
                if isinstance(input_pos, tuple):
                    input_pos = QPoint(*input_pos)
                if isinstance(output_pos, tuple):
                    output_pos = QPoint(*output_pos)
                
                if (event.pos() - input_pos).manhattanLength() < 12:
                    self.is_connecting = True
                    self.start_node_id = node_id
                    self.temp_connection_start = input_pos
                    self.temp_connection_end = event.pos()
                    return
                
                if (event.pos() - output_pos).manhattanLength() < 12:
                    self.is_connecting = True
                    self.start_node_id = node_id
                    self.temp_connection_start = output_pos
                    self.temp_connection_end = event.pos()
                    return
        
        if event.button() == Qt.MouseButton.RightButton:
            node_under_mouse = self._get_node_at_position(event.pos())
            
            if node_under_mouse:
                self.is_connecting = True
                self.start_node_id = node_under_mouse
                widget = self.nodes[node_under_mouse]['widget']
                self.temp_connection_start = widget.get_output_port_pos()
                self.temp_connection_end = event.pos()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_connecting:
            self.temp_connection_end = event.pos()
            self.update()
        elif self.dragging_control_point:
            self.control_points[self.dragging_control_point] = event.pos()
            self.update()
        else:
            self._check_connection_hover(event.pos())
            super().mouseMoveEvent(event)
    
    def _check_connection_hover(self, pos):
        new_hovered = None
        for conn in self.connections:
            start_node_id = conn['from']
            end_node_id = conn['to']
            
            if start_node_id in self.nodes and end_node_id in self.nodes:
                start_widget = self.nodes[start_node_id]['widget']
                end_widget = self.nodes[end_node_id]['widget']
                
                start_pos = start_widget.get_output_port_pos()
                end_pos = end_widget.get_input_port_pos()
                
                if self._is_point_near_path(pos, start_pos, end_pos, 10):
                    new_hovered = conn
                    break
        
        if new_hovered != self.hovered_connection:
            self.hovered_connection = new_hovered
            self.update()
    
    def _is_point_near_path(self, point, start, end, threshold):
        if isinstance(start, QPoint):
            start_x, start_y = start.x(), start.y()
            end_x, end_y = end.x(), end.y()
            point_x, point_y = point.x(), point.y()
        else:
            start_x, start_y = start[0], start[1]
            end_x, end_y = end[0], end[1]
            point_x, point_y = point.x(), point.y()
        
        distance = abs(end_y - start_y)
        control_offset = max(distance * 0.4, 50)
        
        mid1_x = start_x
        mid1_y = start_y + control_offset
        mid2_x = end_x
        mid2_y = end_y - control_offset
        
        for t in [0.25, 0.5, 0.75]:
            bezier_x = (1-t)*(1-t)*(1-t)*start_x + 3*(1-t)*(1-t)*t*mid1_x + 3*(1-t)*t*t*mid2_x + t*t*t*end_x
            bezier_y = (1-t)*(1-t)*(1-t)*start_y + 3*(1-t)*(1-t)*t*mid1_y + 3*(1-t)*t*t*mid2_y + t*t*t*end_y
            
            dist = math.sqrt((point_x - bezier_x)**2 + (point_y - bezier_y)**2)
            if dist < threshold:
                return True
        
        return False
    
    def mouseReleaseEvent(self, event):
        if self.dragging_control_point:
            self.dragging_control_point = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.update()
            return
        
        if self.is_connecting and event.button() == Qt.MouseButton.RightButton:
            node_under_mouse = self._get_node_at_position(event.pos())
            
            if node_under_mouse and node_under_mouse != self.start_node_id:
                if not self._connection_exists(self.start_node_id, node_under_mouse):
                    self.connections.append({
                        'from': self.start_node_id,
                        'to': node_under_mouse
                    })
                    self.nodes[self.start_node_id]['connections'].append(node_under_mouse)
                    self.canvas_modified.emit()
                    self.update()
            
            self.is_connecting = False
            self.start_node_id = None
            self.temp_connection_start = None
            self.temp_connection_end = None
            self.update()
        elif self.is_connecting and event.button() == Qt.MouseButton.LeftButton:
            node_under_mouse = self._get_node_at_position(event.pos())
            
            if node_under_mouse and node_under_mouse != self.start_node_id:
                if not self._connection_exists(self.start_node_id, node_under_mouse):
                    self.connections.append({
                        'from': self.start_node_id,
                        'to': node_under_mouse
                    })
                    self.nodes[self.start_node_id]['connections'].append(node_under_mouse)
                    self.canvas_modified.emit()
                    self.update()
            
            self.is_connecting = False
            self.start_node_id = None
            self.temp_connection_start = None
            self.temp_connection_end = None
            self.update()
        else:
            super().mouseReleaseEvent(event)
    
    def _get_node_at_position(self, pos):
        for node_id, node_data in self.nodes.items():
            widget = node_data['widget']
            if widget.geometry().contains(pos):
                return node_id
        return None
    
    def _connection_exists(self, from_node, to_node):
        for conn in self.connections:
            if conn['from'] == from_node and conn['to'] == to_node:
                return True
        return False
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        clicked_connection = None
        clicked_control_point = None
        
        for conn in self.connections:
            start_node_id = conn['from']
            end_node_id = conn['to']
            
            if start_node_id in self.nodes and end_node_id in self.nodes:
                start_widget = self.nodes[start_node_id]['widget']
                end_widget = self.nodes[end_node_id]['widget']
                
                start_pos = start_widget.get_output_port_pos()
                end_pos = end_widget.get_input_port_pos()
                
                if self._is_point_near_path(event.pos(), start_pos, end_pos, 15):
                    clicked_connection = conn
                    break
        
        for conn_key, control_point in self.control_points.items():
            if (event.pos() - control_point).manhattanLength() < 15:
                clicked_control_point = conn_key
                break
        
        if clicked_control_point:
            reset_action = menu.addAction("🔄 重置控制点")
            reset_action.triggered.connect(lambda: self._reset_control_point(clicked_control_point))
            
            delete_action = menu.addAction("🗑️ 删除连接线")
            delete_action.triggered.connect(lambda: self._delete_connection(clicked_control_point))
        elif clicked_connection:
            delete_action = menu.addAction("🗑️ 删除连接线")
            delete_action.triggered.connect(lambda: self._delete_connection_by_conn(clicked_connection))
        
        if menu.actions():
            menu.exec(event.globalPos())
    
    def _reset_control_point(self, conn_key):
        if conn_key in self.control_points:
            del self.control_points[conn_key]
            self.update()
    
    def _delete_connection(self, conn_key):
        parts = conn_key.split('->')
        if len(parts) == 2:
            from_id, to_id = parts
            conn_to_remove = None
            for conn in self.connections:
                if conn['from'] == from_id and conn['to'] == to_id:
                    conn_to_remove = conn
                    break
            
            if conn_to_remove:
                self.connections.remove(conn_to_remove)
                if from_id in self.nodes:
                    if to_id in self.nodes[from_id]['connections']:
                        self.nodes[from_id]['connections'].remove(to_id)
                if conn_key in self.control_points:
                    del self.control_points[conn_key]
                self.canvas_modified.emit()
                self.update()
    
    def _delete_connection_by_conn(self, conn):
        self.connections.remove(conn)
        from_id = conn['from']
        to_id = conn['to']
        
        if from_id in self.nodes and to_id in self.nodes[from_id]['connections']:
            self.nodes[from_id]['connections'].remove(to_id)
        
        conn_key = f"{from_id}->{to_id}"
        if conn_key in self.control_points:
            del self.control_points[conn_key]
        
        self.canvas_modified.emit()
        self.update()
    
    def get_flow_data(self):
        flow_data = {
            'nodes': [],
            'connections': []
        }
        
        for node_id, node_data in self.nodes.items():
            flow_data['nodes'].append({
                'id': node_id,
                'component_id': node_data['component_id'],
                'x': node_data['x'],
                'y': node_data['y'],
                'properties': node_data.get('properties', {})
            })
        
        flow_data['connections'] = self.connections.copy()
        
        return flow_data
    
    def load_flow_data(self, flow_data):
        self.clear_all()
        
        node_id_map = {}
        
        for node in flow_data.get('nodes', []):
            old_id = node['id']
            new_id = self.add_node(node['component_id'], node['x'], node['y'])
            self.nodes[new_id]['properties'] = node.get('properties', {})
            node_id_map[old_id] = new_id
        
        for conn in flow_data.get('connections', []):
            from_id = node_id_map.get(conn['from'])
            to_id = node_id_map.get(conn['to'])
            
            if from_id and to_id:
                self.connections.append({
                    'from': from_id,
                    'to': to_id
                })
                self.nodes[from_id]['connections'].append(to_id)
        
        self.update()


class PropertiesPanel(QWidget):
    property_changed = pyqtSignal(str, str, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_component = None
        self.property_widgets = {}
        self.browser = None
        self.main_window = None
        self._setup_ui()
    
    def set_browser(self, browser):
        self.browser = browser
    
    def set_main_window(self, main_window):
        self.main_window = main_window
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("属性设置")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        
        self.content_widget = QWidget()
        self.content_layout = QFormLayout(self.content_widget)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        layout.addStretch()
    
    def _test_web_open(self):
        url_widget = self.property_widgets.get('url')
        
        if not url_widget:
            QMessageBox.warning(self, "警告", "URL输入框未找到")
            return
        
        url = url_widget.text()
        
        if not url:
            QMessageBox.warning(self, "警告", "请输入URL地址")
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        QMessageBox.information(self, "提示", "即将启动浏览器并打开网页，请稍候...")
        
        try:
            from rpa_yifei.web.browser_controller import BrowserController, BrowserType
            
            if self.main_window and hasattr(self.main_window, 'browser'):
                browser = self.main_window.browser
                if browser and browser.is_running:
                    try:
                        _ = browser.driver.current_url
                    except:
                        browser = None
                else:
                    browser = None
            else:
                browser = None
            
            if not browser:
                browser = BrowserController.connect_to_existing(9222)
                if not browser:
                    QMessageBox.information(self, "提示", "未检测到已打开的浏览器，正在创建新浏览器...")
                    browser = BrowserController(BrowserType.CHROME, use_shared=True)
                    browser.start(headless=False)
                if browser and browser.is_running:
                    if self.main_window:
                        self.main_window.browser = browser
            
            self.set_browser(browser)
            
            browser.navigate(url)
            
            QMessageBox.information(
                self,
                "成功",
                f"✅ 网页已打开：{url}\n\n浏览器已准备好，可以进行元素拾取或测试定位"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开网页失败：{str(e)}")
    
    def _test_locator(self):
        browser = self.browser
        
        if not browser and self.main_window and hasattr(self.main_window, 'browser'):
            browser = self.main_window.browser
            if browser and browser.is_running:
                try:
                    _ = browser.driver.current_url
                except:
                    browser = None
            else:
                browser = None
        
        if not browser:
            from rpa_yifei.web.browser_controller import BrowserController
            browser = BrowserController.connect_to_existing(9222)
            if browser:
                if self.main_window:
                    self.main_window.browser = browser
        
        if not browser:
            QMessageBox.warning(
                self,
                "浏览器未启动",
                "未检测到已打开的浏览器。\n\n请先点击'🌐 打开并测试网页'按钮启动浏览器。"
            )
            return
        
        try:
            _ = browser.driver.current_url
        except:
            QMessageBox.warning(self, "警告", "浏览器连接已断开，请重新打开网页")
            return
        
        self.browser = browser
        
        locator_type_widget = self.property_widgets.get('locator_type')
        locator_value_widget = self.property_widgets.get('locator_value')
        
        if not locator_type_widget or not locator_value_widget:
            QMessageBox.warning(self, "警告", "定位方式或定位值为空")
            return
        
        locator_type = locator_type_widget.currentText()
        locator_value = locator_value_widget.text()
        
        if not locator_value:
            QMessageBox.warning(self, "警告", "请输入定位值")
            return
        
        QMessageBox.information(self, "提示", f"正在等待元素出现（最多10秒）...\n\n定位方式: {locator_type}\n定位值: {locator_value}")
        
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            
            wait = WebDriverWait(self.browser.driver, 10)
            
            if locator_type == 'xpath':
                element = wait.until(EC.presence_of_element_located(('xpath', locator_value)))
            elif locator_type == 'css':
                element = wait.until(EC.presence_of_element_located(('css selector', locator_value)))
            elif locator_type == 'id':
                element = wait.until(EC.presence_of_element_located(('id', locator_value)))
            elif locator_type == 'name':
                element = wait.until(EC.presence_of_element_located(('name', locator_value)))
            elif locator_type == 'class':
                element = wait.until(EC.presence_of_element_located(('class name', locator_value)))
            else:
                element = self.browser._find_element(locator_value, locator_type)
            
            if element:
                rect = element.rect
                self.browser.driver.execute_script("""
                    arguments[0].style.border = '3px solid #FF0000';
                    arguments[0].style.outline = '3px solid #FF0000';
                    arguments[0].style.zIndex = '999999';
                """, element)
                
                self.browser.driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'center'
                    });
                """, element)
                QMessageBox.information(
                    self,
                    "定位成功",
                    f"✅ 元素定位成功！\n\n"
                    f"定位方式: {locator_type}\n"
                    f"定位值: {locator_value}\n\n"
                    f"位置: ({rect['x']:.0f}, {rect['y']:.0f})\n"
                    f"大小: {rect['width']:.0f} x {rect['height']:.0f}\n\n"
                    f"元素已被红色边框高亮显示，3秒后自动取消"
                )
                
                import threading
                def remove_highlight():
                    import time
                    time.sleep(3)
                    try:
                        self.browser.driver.execute_script("""
                            if (arguments[0].style.border) {
                                arguments[0].style.border = '';
                                arguments[0].style.outline = '';
                                arguments[0].style.zIndex = '';
                            }
                        """, element)
                    except:
                        pass
                
                threading.Thread(target=remove_highlight, daemon=True).start()
                
            else:
                QMessageBox.warning(self, "错误", "未找到元素，请检查定位值是否正确")
                
        except TimeoutException:
            QMessageBox.warning(
                self,
                "定位超时",
                f"❌ 元素在10秒内未出现\n\n"
                f"可能原因：\n"
                f"1. 页面还在加载，请等待\n"
                f"2. 定位值不正确\n"
                f"3. 元素在其他frame/iframe中\n\n"
                f"定位方式: {locator_type}\n"
                f"定位值: {locator_value}"
            )
        except Exception as e:
            error_msg = str(e)
            if "no such element" in error_msg.lower():
                QMessageBox.warning(
                    self,
                    "定位失败",
                    f"❌ 找不到元素\n\n"
                    f"可能原因：\n"
                    f"1. 页面还在加载\n"
                    f"2. 定位值不正确\n"
                    f"3. 元素不可见或被遮挡\n"
                    f"4. 元素在iframe中\n\n"
                    f"详细错误：\n{error_msg}"
                )
            else:
                QMessageBox.critical(self, "错误", f"定位失败：{str(e)}")
    
    def set_component(self, component_id, properties=None):
        self.current_component = component_id
        self._clear_properties()
        self._create_properties(component_id, properties or {})
    
    def _clear_properties(self):
        while self.content_layout.count():
            row_item = self.content_layout.takeRow(0)
            if row_item:
                if row_item.fieldItem:
                    widget = row_item.fieldItem.widget()
                    if widget:
                        widget.close()
                if row_item.labelItem:
                    label = row_item.labelItem.widget()
                    if label:
                        label.close()
        self.property_widgets.clear()
    
    def _create_properties(self, component_id, properties=None):
        property_definitions = self._get_property_definitions(component_id)
        
        for prop_name, prop_def in property_definitions.items():
            value = properties.get(prop_name, prop_def.get('default', ''))
            widget = self._create_widget(prop_def, value)
            if widget:
                self.content_layout.addRow(prop_def['label'], widget)
                self.property_widgets[prop_name] = widget
        
        web_components = ['web_click', 'web_input', 'web_get_text', 'web_get_attr']
        if component_id in web_components:
            test_btn = QPushButton("🔍 测试定位")
            test_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            test_btn.clicked.connect(self._test_locator)
            self.content_layout.addRow("", test_btn)
        
        if component_id == 'web_open':
            test_btn = QPushButton("🌐 打开并测试网页")
            test_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            test_btn.clicked.connect(self._test_web_open)
            self.content_layout.addRow("", test_btn)
    
    def _create_widget(self, prop_def, value=None):
        prop_type = prop_def.get('type', 'text')
        value = value if value is not None else prop_def.get('default', '')
        
        if prop_type == 'text':
            widget = QLineEdit()
            widget.setText(str(value))
            widget.textChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        elif prop_type == 'number':
            widget = QSpinBox()
            widget.setMinimum(prop_def.get('min', 0))
            widget.setMaximum(prop_def.get('max', 999999))
            widget.setValue(int(value) if value else prop_def.get('default', 0))
            widget.valueChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        elif prop_type == 'float':
            widget = QDoubleSpinBox()
            widget.setMinimum(prop_def.get('min', 0))
            widget.setMaximum(prop_def.get('max', 999999))
            widget.setValue(float(value) if value else prop_def.get('default', 0))
            widget.valueChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        elif prop_type == 'checkbox':
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.stateChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        elif prop_type == 'combo':
            widget = QComboBox()
            widget.addItems(prop_def.get('options', []))
            widget.setCurrentText(str(value))
            widget.currentTextChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        else:
            widget = QLineEdit()
            widget.setText(str(value))
            widget.textChanged.connect(lambda v, n=prop_def['name']: self.property_changed.emit(self.current_component, n, v))
        
        return widget
    
    def _get_property_definitions(self, component_id):
        definitions = {
            'mouse_click': {
                'x': {'name': 'x', 'label': 'X坐标:', 'type': 'number', 'default': 0},
                'y': {'name': 'y', 'label': 'Y坐标:', 'type': 'number', 'default': 0},
                'button': {'name': 'button', 'label': '鼠标按钮:', 'type': 'combo', 'options': ['left', 'right', 'middle'], 'default': 'left'},
                'clicks': {'name': 'clicks', 'label': '点击次数:', 'type': 'number', 'default': 1},
            },
            'mouse_move': {
                'x': {'name': 'x', 'label': 'X坐标:', 'type': 'number', 'default': 0},
                'y': {'name': 'y', 'label': 'Y坐标:', 'type': 'number', 'default': 0},
                'duration': {'name': 'duration', 'label': '持续时间(秒):', 'type': 'float', 'default': 0.5},
            },
            'keyboard_type': {
                'text': {'name': 'text', 'label': '输入文本:', 'type': 'text', 'default': ''},
                'interval': {'name': 'interval', 'label': '间隔(秒):', 'type': 'float', 'default': 0.05},
            },
            'keyboard_press': {
                'key': {'name': 'key', 'label': '按键:', 'type': 'text', 'default': ''},
            },
            'keyboard_hotkey': {
                'keys': {'name': 'keys', 'label': '快捷键:', 'type': 'text', 'default': 'ctrl+c'},
            },
            'wait_seconds': {
                'seconds': {'name': 'seconds', 'label': '等待秒数:', 'type': 'float', 'default': 1},
            },
            'excel_read': {
                'file_path': {'name': 'file_path', 'label': '文件路径:', 'type': 'text', 'default': ''},
                'sheet_name': {'name': 'sheet_name', 'label': '工作表:', 'type': 'text', 'default': 'Sheet1'},
                'output_variable': {'name': 'output_variable', 'label': '输出变量:', 'type': 'text', 'default': 'excel_data'},
            },
            'excel_write': {
                'file_path': {'name': 'file_path', 'label': '文件路径:', 'type': 'text', 'default': ''},
                'sheet_name': {'name': 'sheet_name', 'label': '工作表:', 'type': 'text', 'default': 'Sheet1'},
                'data': {'name': 'data', 'label': '数据:', 'type': 'text', 'default': ''},
            },
            'email_send': {
                'smtp_server': {'name': 'smtp_server', 'label': 'SMTP服务器:', 'type': 'text', 'default': ''},
                'smtp_port': {'name': 'smtp_port', 'label': 'SMTP端口:', 'type': 'number', 'default': 465},
                'sender': {'name': 'sender', 'label': '发送者:', 'type': 'text', 'default': ''},
                'password': {'name': 'password', 'label': '密码:', 'type': 'text', 'default': ''},
                'recipient': {'name': 'recipient', 'label': '接收者:', 'type': 'text', 'default': ''},
                'subject': {'name': 'subject', 'label': '主题:', 'type': 'text', 'default': ''},
                'body': {'name': 'body', 'label': '内容:', 'type': 'text', 'default': ''},
            },
            'api_request': {
                'url': {'name': 'url', 'label': 'URL:', 'type': 'text', 'default': ''},
                'method': {'name': 'method', 'label': '方法:', 'type': 'combo', 'options': ['GET', 'POST', 'PUT', 'DELETE'], 'default': 'GET'},
                'headers': {'name': 'headers', 'label': '请求头:', 'type': 'text', 'default': '{}'},
                'data': {'name': 'data', 'label': '请求数据:', 'type': 'text', 'default': ''},
                'output_variable': {'name': 'output_variable', 'label': '输出变量:', 'type': 'text', 'default': 'api_response'},
            },
            'db_query': {
                'db_type': {'name': 'db_type', 'label': '数据库类型:', 'type': 'combo', 'options': ['mysql', 'postgresql', 'sqlite'], 'default': 'mysql'},
                'host': {'name': 'host', 'label': '主机:', 'type': 'text', 'default': 'localhost'},
                'port': {'name': 'port', 'label': '端口:', 'type': 'number', 'default': 3306},
                'database': {'name': 'database', 'label': '数据库:', 'type': 'text', 'default': ''},
                'user': {'name': 'user', 'label': '用户名:', 'type': 'text', 'default': ''},
                'password': {'name': 'password', 'label': '密码:', 'type': 'text', 'default': ''},
                'sql': {'name': 'sql', 'label': 'SQL语句:', 'type': 'text', 'default': ''},
                'output_variable': {'name': 'output_variable', 'label': '输出变量:', 'type': 'text', 'default': 'query_result'},
            },
            'web_open': {
                'url': {'name': 'url', 'label': '网址:', 'type': 'text', 'default': ''},
            },
            'web_click': {
                'locator_type': {'name': 'locator_type', 'label': '定位方式:', 'type': 'combo', 'options': ['xpath', 'css', 'id', 'name', 'class'], 'default': 'xpath'},
                'locator_value': {'name': 'locator_value', 'label': '定位值:', 'type': 'text', 'default': ''},
            },
            'web_input': {
                'locator_type': {'name': 'locator_type', 'label': '定位方式:', 'type': 'combo', 'options': ['xpath', 'css', 'id', 'name', 'class'], 'default': 'xpath'},
                'locator_value': {'name': 'locator_value', 'label': '定位值:', 'type': 'text', 'default': ''},
                'text': {'name': 'text', 'label': '输入文本:', 'type': 'text', 'default': ''},
            },
            'web_get_text': {
                'locator_type': {'name': 'locator_type', 'label': '定位方式:', 'type': 'combo', 'options': ['xpath', 'css', 'id', 'name', 'class'], 'default': 'xpath'},
                'locator_value': {'name': 'locator_value', 'label': '定位值:', 'type': 'text', 'default': ''},
                'output_variable': {'name': 'output_variable', 'label': '输出变量:', 'type': 'text', 'default': 'text'},
            },
            'web_get_attr': {
                'locator_type': {'name': 'locator_type', 'label': '定位方式:', 'type': 'combo', 'options': ['xpath', 'css', 'id', 'name', 'class'], 'default': 'xpath'},
                'locator_value': {'name': 'locator_value', 'label': '定位值:', 'type': 'text', 'default': ''},
                'attribute': {'name': 'attribute', 'label': '属性名:', 'type': 'text', 'default': 'href'},
                'output_variable': {'name': 'output_variable', 'label': '输出变量:', 'type': 'text', 'default': 'attr_value'},
            },
            'web_screenshot': {
                'file_path': {'name': 'file_path', 'label': '保存路径:', 'type': 'text', 'default': 'screenshot.png'},
            },
        }
        
        return definitions.get(component_id, {})


class ComponentLibraryWidget(QWidget):
    component_dragged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("组件库")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(220)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        for category, components in ComponentLibrary.COMPONENTS.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout()
            group_layout.setSpacing(5)
            
            flow_layout = FlowLayout()
            flow_layout.setSpacing(10)
            
            for comp in components:
                item = ComponentItemWidget(comp)
                item.clicked.connect(lambda cid: self._start_drag(cid))
                flow_layout.addWidget(item)
            
            group_layout.addLayout(flow_layout)
            group.setLayout(group_layout)
            content_layout.addWidget(group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _start_drag(self, component_id):
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(component_id)
        drag.setMimeData(mime_data)
        
        drag.exec(Qt.DropAction.CopyAction)


class ExecutionLogWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(150)
    
    def log(self, message, level='INFO'):
        timestamp = QTimer().start()
        from datetime import datetime
        timestamp_str = datetime.now().strftime('%H:%M:%S')
        
        colors = {
            'INFO': '#000000',
            'WARNING': '#FFA500',
            'ERROR': '#FF0000',
            'SUCCESS': '#008000'
        }
        
        color = colors.get(level, '#000000')
        self.append(f'<span style="color: gray;">[{timestamp_str}]</span> <span style="color: {color};">[{level}]</span> {message}')


class MainWindow(QMainWindow):
    flow_saved = pyqtSignal(str)
    flow_loaded = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_modified = False
        self.recording = False
        self.running = False
        
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("RPA Studio - 流程自动化工具")
        self.setGeometry(100, 100, 1400, 900)
        
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_central_widget()
        self._create_status_bar()
    
    def _create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出脚本", self)
        export_action.triggered.connect(self._export_script)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu("编辑(&E)")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_action)
        
        clear_action = QAction("清空画布", self)
        clear_action.triggered.connect(self._clear_canvas)
        edit_menu.addAction(clear_action)
        
        run_menu = menubar.addMenu("运行(&R)")
        
        start_action = QAction("开始运行", self)
        start_action.setShortcut(QKeySequence("F5"))
        start_action.triggered.connect(self._run_flow)
        run_menu.addAction(start_action)
        
        pause_action = QAction("暂停", self)
        pause_action.setShortcut(QKeySequence("F6"))
        pause_action.triggered.connect(self._pause_flow)
        run_menu.addAction(pause_action)
        
        stop_action = QAction("停止", self)
        stop_action.setShortcut(QKeySequence("F7"))
        stop_action.triggered.connect(self._stop_flow)
        run_menu.addAction(stop_action)
        
        step_action = QAction("单步执行", self)
        step_action.setShortcut(QKeySequence("F8"))
        step_action.triggered.connect(self._step_run)
        run_menu.addAction(step_action)
        
        record_menu = menubar.addMenu("录制(&R)")
        
        start_record_action = QAction("开始录制", self)
        start_record_action.setShortcut(QKeySequence("F9"))
        start_record_action.triggered.connect(self._start_recording)
        record_menu.addAction(start_record_action)
        
        stop_record_action = QAction("停止录制", self)
        stop_record_action.setShortcut(QKeySequence("F10"))
        stop_record_action.triggered.connect(self._stop_recording)
        record_menu.addAction(stop_record_action)
        
        tools_menu = menubar.addMenu("工具(&T)")
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)
        
        element_picker_action = QAction("元素拾取器", self)
        element_picker_action.triggered.connect(self._show_element_picker)
        tools_menu.addAction(element_picker_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tool_bar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self._new_file)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton("打开")
        open_btn.clicked.connect(self._open_file)
        toolbar.addWidget(open_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_file)
        toolbar.addWidget(save_btn)
        
        toolbar.addSeparator()
        
        self.run_btn = QPushButton("▶ 运行")
        self.run_btn.clicked.connect(self._run_flow)
        toolbar.addWidget(self.run_btn)
        
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.clicked.connect(self._pause_flow)
        self.pause_btn.setEnabled(False)
        toolbar.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self._stop_flow)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)
        
        toolbar.addSeparator()
        
        self.record_btn = QPushButton("⏺ 录制")
        self.record_btn.clicked.connect(self._start_recording)
        toolbar.addWidget(self.record_btn)
    
    def _create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        left_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.component_library = ComponentLibraryWidget()
        left_splitter.addWidget(self.component_library)
        
        left_splitter.setStretchFactor(0, 0)
        left_splitter.setSizes([220])
        
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.flow_designer = FlowDesignerWidget()
        self.flow_designer.node_selected.connect(self._on_node_selected)
        self.flow_designer.canvas_modified.connect(self._on_canvas_modified)
        center_splitter.addWidget(self.flow_designer)
        
        self.log_widget = ExecutionLogWidget()
        center_splitter.addWidget(self.log_widget)
        
        center_splitter.setStretchFactor(0, 4)
        center_splitter.setStretchFactor(1, 1)
        
        left_splitter.addWidget(center_splitter)
        
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.properties_panel = PropertiesPanel()
        self.properties_panel.property_changed.connect(self._on_property_changed)
        self.properties_panel.set_main_window(self)
        self.properties_panel.set_browser(None)
        right_splitter.addWidget(self.properties_panel)
        
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setSizes([300])
        
        main_layout.addWidget(left_splitter, 3)
        main_layout.addWidget(right_splitter, 0)
    
    def _create_status_bar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)
        
        self.recording_label = QLabel("")
        self.recording_label.setStyleSheet("color: red; font-weight: bold;")
        self.recording_label.setVisible(False)
        self.statusbar.addPermanentWidget(self.recording_label)
    
    def _new_file(self):
        if self.is_modified:
            reply = QMessageBox.question(
                self, '保存更改', '当前流程未保存，是否保存?',
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        self.flow_designer.clear_all()
        self.current_file = None
        self.is_modified = False
        self._update_window_title()
        self.log_widget.log("已创建新流程", 'SUCCESS')
    
    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开流程", "", "RPA流程文件 (*.rpa);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    flow_data = json.load(f)
                
                self.flow_designer.load_flow_data(flow_data)
                self.current_file = file_path
                self.is_modified = False
                self._update_window_title()
                self.flow_loaded.emit(file_path)
                self.log_widget.log(f"已打开: {file_path}", 'SUCCESS')
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开文件: {str(e)}")
    
    def _save_file(self):
        if not self.current_file:
            self._save_file_as()
            return
        
        try:
            flow_data = self.flow_designer.get_flow_data()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                json.dump(flow_data, f, indent=2, ensure_ascii=False)
            
            self.is_modified = False
            self._update_window_title()
            self.flow_saved.emit(self.current_file)
            self.log_widget.log(f"已保存: {self.current_file}", 'SUCCESS')
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法保存文件: {str(e)}")
    
    def _save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存流程", "", "RPA流程文件 (*.rpa);;所有文件 (*.*)"
        )
        
        if file_path:
            if not file_path.endswith('.rpa'):
                file_path += '.rpa'
            
            self.current_file = file_path
            self._save_file()
    
    def _export_script(self):
        flow_data = self.flow_designer.get_flow_data()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出脚本", "", "Python文件 (*.py);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                script_content = self._generate_script(flow_data)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                self.log_widget.log(f"已导出脚本: {file_path}", 'SUCCESS')
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法导出脚本: {str(e)}")
    
    def _generate_script(self, flow_data):
        script_lines = [
            "#!/usr/bin/env python",
            "# -*- coding: utf-8 -*-",
            "",
            "import time",
            "from rpa_yifei.core import GUIAutomation, DataHandler, FlowEngine",
            "",
            "",
            "def main():",
            "    gui = GUIAutomation()",
            "    data_handler = DataHandler()",
            "    flow_engine = FlowEngine()",
            "",
        ]
        
        for node in flow_data.get('nodes', []):
            component_id = node['component_id']
            x, y = node.get('x', 0), node.get('y', 0)
            props = node.get('properties', {})
            
            script_lines.append(f"    # {component_id} at ({x}, {y})")
            
            if component_id == 'mouse_click':
                x = props.get('x', 0)
                y = props.get('y', 0)
                script_lines.append(f"    gui.click({x}, {y})")
            
            elif component_id == 'keyboard_type':
                text = props.get('text', '').replace('\\n', '\\\\n')
                script_lines.append(f'    gui.type_text("{text}")')
            
            elif component_id == 'wait_seconds':
                seconds = props.get('seconds', 1)
                script_lines.append(f"    time.sleep({seconds})")
            
            script_lines.append("")
        
        script_lines.extend([
            "",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ])
        
        return '\n'.join(script_lines)
    
    def _delete_selected(self):
        if self.flow_designer.selected_node:
            self.flow_designer.remove_node(self.flow_designer.selected_node)
            self.flow_designer.selected_node = None
    
    def _clear_canvas(self):
        reply = QMessageBox.question(
            self, '清空画布', '确定要清空画布吗?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.flow_designer.clear_all()
            self.log_widget.log("画布已清空", 'INFO')
    
    def _run_flow(self):
        if not self.flow_designer.nodes:
            QMessageBox.warning(self, "警告", "请先添加组件到流程中")
            return
        
        if not self.flow_designer.connections:
            QMessageBox.warning(
                self,
                "警告",
                "请先连接组件形成流程！\n\n"
                "连接方法：\n"
                "1. 右键点击第一个组件\n"
                "2. 拖拽到下一个组件\n"
                "3. 松开鼠标创建连接\n\n"
                "💡 提示：组件需要按顺序连接才能执行"
            )
            return
        
        self.running = True
        self.run_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.status_label.setText("运行中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.log_widget.log("开始运行流程...", 'INFO')
        
        QTimer.singleShot(100, self._execute_flow)
    
    def _execute_flow(self):
        try:
            execution_order = self._get_execution_order()
            
            if not execution_order:
                self.log_widget.log("无法确定执行顺序，请检查组件连接", 'ERROR')
                self._flow_finished()
                return
            
            self.log_widget.log(f"执行顺序: {' → '.join(execution_order)}", 'INFO')
            
            self._execute_node_sequence(execution_order, 0)
            
        except Exception as e:
            self.log_widget.log(f"执行失败: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self._flow_finished()
    
    def _get_execution_order(self):
        if not self.flow_designer.connections:
            return []
        
        in_degree = {node_id: 0 for node_id in self.flow_designer.nodes.keys()}
        
        for conn in self.flow_designer.connections:
            if conn['to'] in in_degree:
                in_degree[conn['to']] += 1
        
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for conn in self.flow_designer.connections:
                if conn['from'] == current:
                    in_degree[conn['to']] -= 1
                    if in_degree[conn['to']] == 0:
                        queue.append(conn['to'])
        
        if len(result) == len(self.flow_designer.nodes):
            return result
        else:
            self.log_widget.log("检测到循环依赖或断开连接", 'WARNING')
            return result
    
    def _execute_node_sequence(self, order, index):
        if index >= len(order):
            self.log_widget.log("✅ 流程执行完成！", 'SUCCESS')
            self._flow_finished()
            return
        
        if not self.running:
            self.log_widget.log("流程已停止", 'WARNING')
            return
        
        node_id = order[index]
        node_data = self.flow_designer.nodes[node_id]
        component_id = node_data['component_id']
        properties = node_data.get('properties', {})
        
        self.log_widget.log(f"执行 [{index + 1}/{len(order)}]: {node_id} ({component_id})", 'INFO')
        
        try:
            success = self._execute_component(component_id, properties)
            
            if success:
                self.log_widget.log(f"✅ {node_id} 执行成功", 'SUCCESS')
            else:
                self.log_widget.log(f"⚠️ {node_id} 执行失败", 'WARNING')
            
            QTimer.singleShot(500, lambda: self._execute_node_sequence(order, index + 1))
            
        except Exception as e:
            self.log_widget.log(f"❌ {node_id} 执行错误: {str(e)}", 'ERROR')
            self._flow_finished()
    
    def _execute_component(self, component_id, properties):
        if component_id == 'web_open':
            return self._execute_web_open(properties)
        elif component_id == 'web_click':
            return self._execute_web_click(properties)
        elif component_id == 'web_input':
            return self._execute_web_input(properties)
        elif component_id == 'web_get_text':
            return self._execute_web_get_text(properties)
        elif component_id == 'wait_seconds':
            import time
            seconds = float(properties.get('seconds', 1))
            self.log_widget.log(f"等待 {seconds} 秒...", 'INFO')
            time.sleep(seconds)
            return True
        elif component_id == 'output_message':
            msg = properties.get('message', '')
            QMessageBox.information(self, "消息", msg)
            return True
        elif component_id == 'output_log':
            msg = properties.get('message', '')
            self.log_widget.log(f"[输出] {msg}", 'INFO')
            return True
        else:
            self.log_widget.log(f"组件 {component_id} 暂未实现", 'WARNING')
            return True
    
    def _check_browser_available(self):
        if not hasattr(self, 'browser') or not self.browser:
            return False
        
        if not self.browser.is_running:
            return False
        
        try:
            _ = self.browser.driver.current_url
            return True
        except:
            return False
    
    def _execute_web_open(self, properties):
        url = properties.get('url', '')
        if not url:
            self.log_widget.log("⚠️ URL为空", 'WARNING')
            return False
        
        self.log_widget.log(f"🌐 打开网页: {url}", 'INFO')
        
        browser_needed = False
        
        if not hasattr(self, 'browser') or not self.browser:
            browser_needed = True
        elif not self.browser.is_running:
            browser_needed = True
        else:
            try:
                _ = self.browser.driver.current_url
            except:
                browser_needed = True
        
        if browser_needed:
            try:
                if hasattr(self, 'browser') and self.browser:
                    try:
                        self.browser.close()
                    except:
                        pass
                
                from rpa_yifei.web.browser_controller import BrowserController, BrowserType
                self.browser = BrowserController.get_shared_instance()
                if self.browser:
                    self.log_widget.log("✅ 复用已登录的浏览器", 'SUCCESS')
                else:
                    self.browser = BrowserController(BrowserType.CHROME, use_shared=True)
                    self.browser.start(headless=False)
                    self.log_widget.log("✅ 浏览器已启动", 'SUCCESS')
            except Exception as e:
                self.log_widget.log(f"❌ 启动浏览器失败: {str(e)}", 'ERROR')
                return False
        
        self.properties_panel.set_browser(self.browser)
        
        try:
            self.browser.navigate(url)
            self.log_widget.log(f"✅ 已导航到: {url}", 'SUCCESS')
            return True
        except Exception as e:
            error_msg = str(e)
            if "no such window" in error_msg.lower() or "target window already closed" in error_msg.lower():
                self.log_widget.log("⚠️ 浏览器窗口已关闭，正在重新启动...", 'WARNING')
                try:
                    self.browser.close()
                except:
                    pass
                
                from rpa_yifei.web.browser_controller import BrowserController, BrowserType
                self.browser = BrowserController.get_shared_instance()
                if self.browser:
                    self.log_widget.log("✅ 复用已登录的浏览器", 'SUCCESS')
                else:
                    self.browser = BrowserController(BrowserType.CHROME, use_shared=True)
                    self.browser.start(headless=False)
                    self.log_widget.log("✅ 浏览器已重新启动", 'SUCCESS')
                
                self.properties_panel.set_browser(self.browser)
                
                try:
                    self.browser.navigate(url)
                    self.log_widget.log(f"✅ 已导航到: {url}", 'SUCCESS')
                    return True
                except Exception as e2:
                    self.log_widget.log(f"❌ 重新导航失败: {str(e2)}", 'ERROR')
                    return False
            else:
                self.log_widget.log(f"❌ 导航失败: {str(e)}", 'ERROR')
                return False
    
    def _execute_web_click(self, properties):
        if not self._check_browser_available():
            self.log_widget.log("❌ 浏览器未启动或已关闭", 'ERROR')
            return False
        
        locator_type = properties.get('locator_type', 'xpath')
        locator_value = properties.get('locator_value', '')
        
        if not locator_value:
            self.log_widget.log("⚠️ 定位值为空", 'WARNING')
            return False
        
        try:
            self.browser.click_element(locator_value, locator_type)
            self.log_widget.log(f"✅ 点击成功: {locator_type}={locator_value}", 'SUCCESS')
            return True
        except Exception as e:
            self.log_widget.log(f"❌ 点击失败: {str(e)}", 'ERROR')
            return False
    
    def _execute_web_input(self, properties):
        if not self._check_browser_available():
            self.log_widget.log("❌ 浏览器未启动或已关闭", 'ERROR')
            return False
        
        locator_type = properties.get('locator_type', 'xpath')
        locator_value = properties.get('locator_value', '')
        text = properties.get('text', '')
        
        if not locator_value:
            self.log_widget.log("⚠️ 定位值为空", 'WARNING')
            return False
        
        try:
            self.browser.input_text(locator_value, text, locator_type)
            self.log_widget.log(f"✅ 输入成功: {text}", 'SUCCESS')
            return True
        except Exception as e:
            self.log_widget.log(f"❌ 输入失败: {str(e)}", 'ERROR')
            return False
    
    def _execute_web_get_text(self, properties):
        if not self._check_browser_available():
            self.log_widget.log("❌ 浏览器未启动或已关闭", 'ERROR')
            return False
        
        locator_type = properties.get('locator_type', 'xpath')
        locator_value = properties.get('locator_value', '')
        
        if not locator_value:
            self.log_widget.log("⚠️ 定位值为空", 'WARNING')
            return False
        
        try:
            element = self.browser._find_element(locator_value, locator_type)
            text = element.text if element else ''
            self.log_widget.log(f"✅ 获取文本: {text[:50]}{'...' if len(text) > 50 else ''}", 'SUCCESS')
            return True
        except Exception as e:
            self.log_widget.log(f"❌ 获取文本失败: {str(e)}", 'ERROR')
            return False
    
    def _flow_finished(self):
        self.running = False
        self.run_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        self.status_label.setText("执行完成")
        self.progress_bar.setVisible(False)
    
    def _pause_flow(self):
        self.status_label.setText("已暂停")
        self.pause_btn.setEnabled(False)
        self.log_widget.log("流程已暂停", 'WARNING')
    
    def _stop_flow(self):
        self.running = False
        self.run_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        self.status_label.setText("已停止")
        self.progress_bar.setVisible(False)
        
        self.log_widget.log("流程已停止", 'WARNING')
    
    def _step_run(self):
        self.log_widget.log("单步执行...", 'INFO')
    
    def _start_recording(self):
        self.recording = True
        self.record_btn.setText("⏹ 停止")
        self.record_btn.clicked.disconnect()
        self.record_btn.clicked.connect(self._stop_recording)
        
        self.recording_label.setText("● 录制中")
        self.recording_label.setVisible(True)
        
        self.log_widget.log("开始录制操作...", 'INFO')
    
    def _stop_recording(self):
        self.recording = False
        self.record_btn.setText("⏺ 录制")
        self.record_btn.clicked.disconnect()
        self.record_btn.clicked.connect(self._start_recording)
        
        self.recording_label.setVisible(False)
        
        self.log_widget.log("录制已停止", 'SUCCESS')
    
    def _show_settings(self):
        QMessageBox.information(self, "设置", "设置功能开发中...")
    
    def _show_element_picker(self):
        try:
            from rpa_yifei.web.element_picker import create_element_picker
            
            if create_element_picker is None:
                QMessageBox.warning(self, "错误", "Selenium未安装，无法启动元素拾取器\n请运行: pip install selenium webdriver-manager")
                return
            
            self.element_picker_window = create_element_picker()
            if self.element_picker_window:
                self.element_picker_window.element_selected.connect(self._on_element_selected)
                self.element_picker_window.show()
                self.log_widget.log("元素拾取器已启动", 'INFO')
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动元素拾取器: {str(e)}")
    
    def _on_element_selected(self, element_data: dict):
        self.log_widget.log(f"选择元素: {element_data['locator_type']} = {element_data['locator_value']}", 'SUCCESS')
        
        if self.flow_designer.selected_node:
            node_id = self.flow_designer.selected_node
            component_id = self.flow_designer.nodes[node_id]['component_id']
            
            self.flow_designer.nodes[node_id]['properties']['locator_type'] = element_data['locator_type']
            self.flow_designer.nodes[node_id]['properties']['locator_value'] = element_data['locator_value']
            
            if 'tag' in element_data and element_data['tag']:
                self.flow_designer.nodes[node_id]['properties']['tag'] = element_data['tag']
            if 'xpath' in element_data and element_data['xpath']:
                self.flow_designer.nodes[node_id]['properties']['xpath'] = element_data['xpath']
            if 'css' in element_data and element_data['css']:
                self.flow_designer.nodes[node_id]['properties']['css'] = element_data['css']
            
            self.properties_panel.set_component(component_id, self.flow_designer.nodes[node_id]['properties'])
            
            QMessageBox.information(
                self,
                "元素已保存",
                f"✅ 元素信息已成功保存到选中的组件\n\n"
                f"定位方式: {element_data['locator_type']}\n"
                f"定位值: {element_data['locator_value']}\n"
                f"标签: {element_data.get('tag', 'N/A')}\n\n"
                f"💡 提示: 可以在右侧属性面板中修改定位值"
            )
        else:
            QMessageBox.warning(
                self,
                "未选中组件",
                "⚠️ 请先在流程设计器中选择一个浏览器组件\n"
                "（如：点击元素、输入文本、获取文本等）\n\n"
                "操作步骤：\n"
                "1. 从左侧组件库拖拽一个浏览器组件到画布\n"
                "2. 点击选中该组件\n"
                "3. 再次点击\"拾取元素\"即可保存"
            )
    
    def _show_about(self):
        QMessageBox.about(
            self, "关于 RPA Studio",
            "RPA Studio v1.0.0\n\n"
            "机器人流程自动化工具\n\n"
            "功能特点:\n"
            "• 可视化流程设计\n"
            "• 鼠标键盘自动化\n"
            "• Excel/文件/邮件处理\n"
            "• API/数据库集成\n"
            "• 操作录制\n"
            "• 定时任务调度"
        )
    
    def _on_node_selected(self, node_id):
        if node_id in self.flow_designer.nodes:
            component_id = self.flow_designer.nodes[node_id]['component_id']
            properties = self.flow_designer.nodes[node_id]['properties']
            self.properties_panel.set_component(component_id, properties)
    
    def _on_property_changed(self, component_id, property_name, value):
        if self.flow_designer.selected_node:
            node_id = self.flow_designer.selected_node
            self.flow_designer.nodes[node_id]['properties'][property_name] = value
            self.log_widget.log(f"属性已更新: {property_name} = {value}", 'INFO')
        
        self.is_modified = True
        self._update_window_title()
    
    def _on_canvas_modified(self):
        self.is_modified = True
        self._update_window_title()
    
    def _update_window_title(self):
        title = "RPA Studio - 流程自动化工具"
        
        if self.current_file:
            import os
            title += f" - {os.path.basename(self.current_file)}"
        
        if self.is_modified:
            title += " *"
        
        self.setWindowTitle(title)
    
    def closeEvent(self, event: QCloseEvent):
        if self.is_modified:
            reply = QMessageBox.question(
                self, '保存更改', '当前流程未保存，是否保存?',
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
