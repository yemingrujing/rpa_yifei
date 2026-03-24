import sys
import time
import threading
from typing import Optional, Callable, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QListWidget, QListWidgetItem, QFrame, QScrollArea,
    QSplitter, QGroupBox, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QThread
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

try:
    from .browser_controller import BrowserController, BrowserType, ElementInfo
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    BrowserController = None
    BrowserType = None
    
    class ElementInfo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        def to_dict(self):
            return self.__dict__


class BrowserThread(QThread):
    finished = pyqtSignal(bool, str)
    elements_loaded = pyqtSignal(list)
    status_changed = pyqtSignal(str)
    
    def __init__(self, browser_controller, url=""):
        super().__init__()
        self.browser = browser_controller
        self.url = url
        self._is_running = True
    
    def run(self):
        try:
            if not self.browser.is_running:
                self.status_changed.emit("正在启动浏览器...")
                self.browser.start(headless=False)
                time.sleep(3)
            
            if self.url:
                self.status_changed.emit(f"正在加载 {self.url}...")
                try:
                    self.browser.navigate(self.url)
                except Exception as nav_error:
                    error_msg = str(nav_error)
                    if "timeout" in error_msg.lower():
                        self.finished.emit(False, "页面加载超时，请检查网络连接")
                    elif "connection" in error_msg.lower():
                        self.finished.emit(False, "连接失败，请检查网络或浏览器状态")
                    else:
                        self.finished.emit(False, f"导航失败: {error_msg}")
                    return
                
                time.sleep(3)
                
                self.status_changed.emit("正在获取页面元素...")
                try:
                    elements = self.browser.get_all_elements()[:100]
                except Exception as elem_error:
                    self.finished.emit(False, f"获取元素失败: {str(elem_error)}")
                    return
                
                element_infos = []
                for elem in elements:
                    try:
                        info = self.browser.get_element_info(elem)
                        element_infos.append(info)
                    except:
                        continue
                
                self.elements_loaded.emit(element_infos)
                self.finished.emit(True, "加载成功")
            else:
                self.finished.emit(True, "浏览器已启动")
                
        except Exception as e:
            error_msg = str(e)
            if "ConnectionAbortedError" in error_msg or "10053" in error_msg:
                self.finished.emit(False, "浏览器连接被拒绝，请确保Chrome已关闭或尝试重启程序")
            elif "No such file or directory" in error_msg or "chromedriver" in error_msg.lower():
                self.finished.emit(False, "ChromeDriver未找到，请运行: pip install webdriver-manager")
            else:
                self.finished.emit(False, f"操作失败: {error_msg}")
    
    def stop(self):
        self._is_running = False


class ElementPickerWidget(QFrame):
    element_selected = pyqtSignal(dict)
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser = None
        self.selected_elements: List[ElementInfo] = []
        self.current_element = None
        self.is_picking_mode = False
        self.browser_thread = None
        self.pick_timer = QTimer()
        self.pick_timer.timeout.connect(self._check_picked_element)
        
        self.setWindowTitle("元素拾取器")
        self.setMinimumSize(900, 700)
        self.setFrameStyle(QFrame.Shape.Box)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入URL地址...")
        self.url_input.returnPressed.connect(self._navigate_to_url)
        
        self.navigate_btn = QPushButton("访问")
        self.navigate_btn.clicked.connect(self._navigate_to_url)
        
        header.addWidget(QLabel("URL:"))
        header.addWidget(self.url_input)
        header.addWidget(self.navigate_btn)
        
        layout.addLayout(header)
        
        control_bar = QHBoxLayout()
        
        self.pick_btn = QPushButton("🎯 拾取元素")
        self.pick_btn.setCheckable(True)
        self.pick_btn.clicked.connect(self._toggle_pick_mode)
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._refresh_elements)
        
        self.save_btn = QPushButton("💾 保存选择")
        self.save_btn.clicked.connect(self._save_selected)
        
        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.clicked.connect(self.close)
        
        control_bar.addWidget(self.pick_btn)
        control_bar.addWidget(self.refresh_btn)
        control_bar.addWidget(self.save_btn)
        control_bar.addStretch()
        control_bar.addWidget(self.close_btn)
        
        layout.addLayout(control_bar)
        
        self.status_label = QLabel("状态: 未连接")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setVisible(False)
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        elements_group = QGroupBox("页面元素列表")
        elements_layout = QVBoxLayout(elements_group)
        
        self.elements_list = QListWidget()
        self.elements_list.itemClicked.connect(self._on_element_clicked)
        self.elements_list.setMaximumWidth(300)
        elements_layout.addWidget(self.elements_list)
        
        left_layout.addWidget(elements_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索元素...")
        self.search_input.textChanged.connect(self._filter_elements)
        left_layout.addWidget(self.search_input)
        
        splitter.addWidget(left_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        tabs = QTabWidget()
        
        info_tab = QWidget()
        info_layout = QFormLayout(info_tab)
        
        self.tag_input = QLineEdit()
        self.tag_input.setReadOnly(True)
        info_layout.addRow("标签:", self.tag_input)
        
        self.id_input = QLineEdit()
        self.id_input.setReadOnly(True)
        info_layout.addRow("ID:", self.id_input)
        
        self.name_input = QLineEdit()
        self.name_input.setReadOnly(True)
        info_layout.addRow("Name:", self.name_input)
        
        self.class_input = QLineEdit()
        self.class_input.setReadOnly(True)
        info_layout.addRow("Class:", self.class_input)
        
        self.text_input = QTextEdit()
        self.text_input.setReadOnly(True)
        self.text_input.setMaximumHeight(80)
        info_layout.addRow("Text:", self.text_input)
        
        self.href_input = QLineEdit()
        self.href_input.setReadOnly(True)
        info_layout.addRow("Href:", self.href_input)
        
        self.src_input = QLineEdit()
        self.src_input.setReadOnly(True)
        info_layout.addRow("Src:", self.src_input)
        
        right_layout.addWidget(info_tab)
        
        locator_tab = QWidget()
        locator_layout = QFormLayout(locator_tab)
        
        self.xpath_input = QLineEdit()
        self.xpath_input.setReadOnly(True)
        locator_layout.addRow("XPath:", self.xpath_input)
        
        self.css_input = QLineEdit()
        self.css_input.setReadOnly(True)
        locator_layout.addRow("CSS:", self.css_input)
        
        self.locator_type_combo = QComboBox()
        self.locator_type_combo.addItems(['xpath', 'css', 'id', 'name', 'class', 'tag'])
        locator_layout.addRow("定位方式:", self.locator_type_combo)
        
        self.locator_value_input = QLineEdit()
        locator_layout.addRow("定位值:", self.locator_value_input)
        
        use_locator_btn = QPushButton("使用此定位器")
        use_locator_btn.clicked.connect(self._use_current_locator)
        locator_layout.addRow("", use_locator_btn)
        
        right_layout.addWidget(locator_tab)
        
        actions_tab = QWidget()
        actions_layout = QVBoxLayout(actions_tab)
        
        self.action_combo = QComboBox()
        self.action_combo.addItems(['点击', '输入文本', '获取文本', '获取属性', '悬停', '截图'])
        actions_layout.addWidget(QLabel("选择操作:"))
        actions_layout.addWidget(self.action_combo)
        
        self.action_param_input = QLineEdit()
        self.action_param_input.setPlaceholderText("参数（如输入文本）")
        actions_layout.addWidget(self.action_param_input)
        
        test_action_btn = QPushButton("测试操作")
        test_action_btn.clicked.connect(self._test_action)
        actions_layout.addWidget(test_action_btn)
        
        add_to_list_btn = QPushButton("添加到组件")
        add_to_list_btn.clicked.connect(self._add_to_component)
        actions_layout.addWidget(add_to_list_btn)
        
        actions_layout.addStretch()
        right_layout.addWidget(actions_tab)
        
        tabs.addTab(info_tab, "元素信息")
        tabs.addTab(locator_tab, "定位器")
        tabs.addTab(actions_tab, "操作测试")
        
        right_layout.addWidget(tabs)
        
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter, 1)
    
    def _navigate_to_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        if not self.browser:
            if not SELENIUM_AVAILABLE:
                QMessageBox.warning(self, "错误", "Selenium未安装，无法启动浏览器")
                return
            
            try:
                shared_browser = BrowserController.get_shared_instance()
                if shared_browser:
                    self.browser = shared_browser
                    self.status_label.setText("状态: 使用已登录的浏览器...")
                else:
                    self.browser = BrowserController(BrowserType.CHROME, use_shared=True)
            except Exception as e:
                print(f"Failed to use shared browser: {e}")
                self.browser = BrowserController(BrowserType.CHROME, use_shared=True)
        
        self.navigate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status_label.setText("状态: 正在启动浏览器...")
        
        self.browser_thread = BrowserThread(self.browser, url)
        self.browser_thread.status_changed.connect(self._on_status_changed)
        self.browser_thread.elements_loaded.connect(self._on_elements_loaded)
        self.browser_thread.finished.connect(self._on_browser_finished)
        self.browser_thread.start()
    
    def _on_status_changed(self, status: str):
        self.status_label.setText(f"状态: {status}")
    
    def _on_elements_loaded(self, elements: List):
        self.selected_elements = elements
        self.elements_list.clear()
        
        for info in elements:
            display_text = f"[{info.tag_name}]"
            if info.id:
                display_text += f" #{info.id}"
            if info.class_name:
                cls = info.class_name.split()[0] if info.class_name else ""
                display_text += f" .{cls}"
            if info.text and len(info.text) < 30:
                display_text += f" '{info.text}'"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, info)
            self.elements_list.addItem(item)
        
        self.status_label.setText(f"状态: 发现 {len(elements)} 个元素")
    
    def _on_browser_finished(self, success: bool, message: str):
        self.navigate_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if success:
            self.status_label.setText(f"状态: {message}")
        else:
            QMessageBox.warning(self, "错误", f"操作失败: {message}")
            self.status_label.setText("状态: 操作失败")
    
    def _refresh_elements(self):
        if not self.browser or not self.browser.is_running:
            QMessageBox.warning(self, "警告", "请先访问一个网址")
            return
        
        self.progress.setVisible(True)
        self.status_label.setText("状态: 正在获取元素...")
        
        self.browser_thread = BrowserThread(self.browser, "")
        self.browser_thread.status_changed.connect(self._on_status_changed)
        self.browser_thread.elements_loaded.connect(self._on_elements_loaded)
        self.browser_thread.finished.connect(self._on_browser_finished)
        self.browser_thread.start()
    
    def _filter_elements(self, text: str):
        for i in range(self.elements_list.count()):
            item = self.elements_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def _on_element_clicked(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole)
        if info:
            self._display_element_info(info)
    
    def _display_element_info(self, info: ElementInfo):
        self.current_element = info
        
        self.tag_input.setText(info.tag_name)
        self.id_input.setText(info.id or "")
        self.name_input.setText(info.name or "")
        self.class_input.setText(info.class_name or "")
        self.text_input.setPlainText(info.text or "")
        self.href_input.setText(info.href or "")
        self.src_input.setText(info.src or "")
        self.xpath_input.setText(info.xpath)
        self.css_input.setText(info.css_selector)
        
        locator_value = ""
        if info.id:
            locator_value = info.id
            self.locator_type_combo.setCurrentText('id')
        elif info.xpath:
            locator_value = info.xpath
            self.locator_type_combo.setCurrentText('xpath')
        elif info.css_selector:
            locator_value = info.css_selector
            self.locator_type_combo.setCurrentText('css')
        
        self.locator_value_input.setText(locator_value)
    
    def _toggle_pick_mode(self):
        if not self.browser or not self.browser.is_running:
            QMessageBox.warning(self, "警告", "请先访问一个网址")
            return
        
        self.is_picking_mode = not self.is_picking_mode
        
        if self.is_picking_mode:
            self.pick_btn.setText("⏹ 停止拾取")
            self.status_label.setText("状态: 拾取模式 - 按住 Ctrl + 点击鼠标拾取元素")
            
            reply = QMessageBox.information(
                self,
                "元素拾取模式",
                "🎯 元素拾取模式已启用！\n\n"
                "1. 移动鼠标到您想要拾取的页面元素上\n"
                "2. 元素会被蓝色边框高亮显示\n"
                "3. 按住 Ctrl 键，鼠标指针会变成十字准星\n"
                "4. 按住 Ctrl + 点击鼠标即可拾取元素\n"
                "5. 点击\"停止拾取\"按钮退出拾取模式\n\n"
                "💡 提示：使用 Ctrl+点击 可以避免误操作\n\n"
                "是否继续？",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Ok:
                try:
                    self.browser.enable_pick_mode()
                    self.pick_timer.start(200)
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"启用拾取模式失败: {str(e)}")
                    self.is_picking_mode = False
                    self.pick_btn.setText("🎯 拾取元素")
                    self.status_label.setText("状态: 正常模式")
            else:
                self.is_picking_mode = False
                self.pick_btn.setText("🎯 拾取元素")
                self.status_label.setText("状态: 正常模式")
        else:
            self.pick_btn.setText("🎯 拾取元素")
            self.status_label.setText("状态: 正常模式")
            self.pick_timer.stop()
            
            try:
                self.browser.disable_pick_mode()
                QMessageBox.information(self, "提示", "拾取模式已关闭")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"关闭拾取模式失败: {str(e)}")
    
    def _check_picked_element(self):
        if not self.is_picking_mode or not self.browser or not self.browser.is_running:
            return
        
        try:
            script = """
            if (window.__selenium_last_clicked_element) {
                var elem = window.__selenium_last_clicked_element;
                var rect = elem.getBoundingClientRect();
                var xpath = '';
                
                // 优先使用元素自身的属性生成 XPath
                if (elem.id && elem.tagName !== 'BODY' && elem.tagName !== 'HTML') {
                    xpath = "//*[@id='" + elem.id + "']";
                } else if (elem.name && elem.tagName !== 'BODY' && elem.tagName !== 'HTML') {
                    xpath = "//" + elem.tagName.toLowerCase() + "[@name='" + elem.name + "']";
                } else if (elem.getAttribute('placeholder') && elem.tagName !== 'BODY' && elem.tagName !== 'HTML') {
                    xpath = "//" + elem.tagName.toLowerCase() + "[@placeholder='" + elem.getAttribute('placeholder') + "']";
                } else {
                    // 生成相对路径
                    var path = [];
                    var current = elem;
                    while (current && current.nodeType === Node.ELEMENT_NODE && current.tagName !== 'BODY' && current.tagName !== 'HTML') {
                        var ix = 0;
                        var siblings = current.parentNode ? Array.from(current.parentNode.children) : [];
                        for (var i = 0; i < siblings.length; i++) {
                            if (siblings[i] === current) {
                                ix++;
                                path.unshift(current.tagName.toLowerCase() + '[' + ix + ']');
                                break;
                            }
                            if (siblings[i].nodeType === 1 && siblings[i].tagName === current.tagName) {
                                ix++;
                            }
                        }
                        current = current.parentNode;
                    }
                    xpath = '//' + path.join('/');
                }
                
                var result = {
                    'tag': elem.tagName.toLowerCase(),
                    'id': elem.id || null,
                    'name': elem.getAttribute('name') || null,
                    'class': elem.className || null,
                    'text': elem.innerText || null,
                    'href': elem.href || null,
                    'src': elem.src || null,
                    'placeholder': elem.getAttribute('placeholder') || null,
                    'xpath': xpath,
                    'rect': {
                        'x': rect.x,
                        'y': rect.y,
                        'width': rect.width,
                        'height': rect.height
                    }
                };
                
                delete window.__selenium_last_clicked_element;
                return JSON.stringify(result);
            }
            return null;
            """
            
            result = self.browser.driver.execute_script(script)
            
            if result:
                import json
                data = json.loads(result)
                
                css_script = """
                function getCssSelector(el) {
                    if (!el) return '';
                    
                    // 优先使用元素的 id
                    if (el.id) return '#' + el.id;
                    
                    // 使用元素的 name 属性
                    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
                    
                    // 使用元素的 placeholder
                    var placeholder = el.getAttribute('placeholder');
                    if (placeholder) return el.tagName.toLowerCase() + '[placeholder="' + placeholder + '"]';
                    
                    // 生成相对路径
                    var path = [];
                    while (el && el.nodeType === 1 && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
                        var selector = el.tagName.toLowerCase();
                        if (el.id) {
                            selector += '#' + el.id;
                            path.unshift(selector);
                            break;
                        } else {
                            var siblings = el.parentNode ? Array.from(el.parentNode.children) : [];
                            var index = 0;
                            for (var i = 0; i < siblings.length; i++) {
                                if (siblings[i].nodeType === 1 && siblings[i].tagName === el.tagName) {
                                    index++;
                                }
                                if (siblings[i] === el) break;
                            }
                            selector += ':nth-of-type(' + index + ')';
                        }
                        path.unshift(selector);
                        el = el.parentNode;
                    }
                    return path.join(' > ');
                }
                
                var elem = document.elementFromPoint(arguments[0], arguments[1]);
                return getCssSelector(elem);
                """
                
                element_info = ElementInfo(
                    tag_name=data['tag'],
                    id=data['id'],
                    name=data['name'],
                    class_name=data['class'],
                    xpath=data['xpath'],
                    css_selector='',
                    text=data['text'],
                    href=data['href'],
                    src=data['src'],
                    rect=data['rect'],
                    attributes={}
                )
                
                try:
                    center_x = data['rect']['x'] + data['rect']['width'] / 2
                    center_y = data['rect']['y'] + data['rect']['height'] / 2
                    element_info.css_selector = self.browser.driver.execute_script(
                        css_script, center_x, center_y
                    )
                except Exception as e:
                    pass
                
                self._display_element_info(element_info)
                self.status_label.setText(f"状态: ✅ 已拾取元素: <{data['tag']}>")
                
                QMessageBox.information(
                    self,
                    "元素拾取成功",
                    f"✅ 成功拾取元素！\n\n"
                    f"标签: <{data['tag']}>\n"
                    f"ID: {data['id'] or '无'}\n"
                    f"Class: {data['class'] or '无'}\n"
                    f"XPath: {data['xpath'][:50]}..."
                )
                
                self.is_picking_mode = False
                self.pick_btn.setText("🎯 拾取元素")
                self.pick_timer.stop()
                self.browser.disable_pick_mode()
                
        except Exception as e:
            pass
    
    def _use_current_locator(self):
        locator_type = self.locator_type_combo.currentText()
        locator_value = self.locator_value_input.text()
        
        if not locator_value:
            QMessageBox.warning(self, "警告", "请先选择一个元素")
            return
        
        element_data = {
            'locator_type': locator_type,
            'locator_value': locator_value,
            'tag': self.tag_input.text(),
            'id': self.id_input.text(),
            'xpath': self.xpath_input.text(),
            'css': self.css_input.text()
        }
        
        self.element_selected.emit(element_data)
        QMessageBox.information(self, "成功", f"已设置定位器:\n类型: {locator_type}\n值: {locator_value}")
    
    def _test_action(self):
        if not self.browser or not self.current_element:
            QMessageBox.warning(self, "警告", "请先选择一个元素")
            return
        
        locator_type = self.locator_type_combo.currentText()
        locator_value = self.locator_value_input.text()
        
        try:
            action = self.action_combo.currentText()
            param = self.action_param_input.text()
            
            if action == '点击':
                self.browser.click_element(locator_value, locator_type)
                self.status_label.setText("状态: 点击成功")
            
            elif action == '输入文本':
                self.browser.input_text(locator_value, param, locator_type)
                self.status_label.setText(f"状态: 输入文本成功: {param}")
            
            elif action == '获取文本':
                element = self.browser._find_element(locator_value, locator_type)
                text = element.text if element else ""
                QMessageBox.information(self, "文本内容", text)
            
            elif action == '截图':
                screenshot = self.browser.take_screenshot()
                QMessageBox.information(self, "截图", "截图已保存")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"操作失败: {str(e)}")
    
    def _add_to_component(self):
        self._use_current_locator()
    
    def _save_selected(self):
        if not self.current_element:
            QMessageBox.warning(self, "警告", "请先选择一个元素")
            return
        
        self._use_current_locator()
    
    def closeEvent(self, event):
        if self.pick_timer and self.pick_timer.isActive():
            self.pick_timer.stop()
        if self.is_picking_mode and self.browser:
            try:
                self.browser.disable_pick_mode()
            except:
                pass
        if self.browser_thread and self.browser_thread.isRunning():
            self.browser_thread.stop()
            self.browser_thread.wait()
        if self.browser:
            self.browser.close()
        self.closed.emit()
        super().closeEvent(event)


def create_element_picker() -> Optional[ElementPickerWidget]:
    if not SELENIUM_AVAILABLE:
        return None
    return ElementPickerWidget()
