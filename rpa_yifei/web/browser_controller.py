import time
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class BrowserType(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    IE = "ie"


@dataclass
class ElementInfo:
    tag_name: str
    id: Optional[str]
    name: Optional[str]
    class_name: Optional[str]
    xpath: str
    css_selector: str
    text: Optional[str]
    href: Optional[str]
    src: Optional[str]
    rect: Dict[str, int]
    attributes: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tag_name': self.tag_name,
            'id': self.id,
            'name': self.name,
            'class_name': self.class_name,
            'xpath': self.xpath,
            'css_selector': self.css_selector,
            'text': self.text,
            'href': self.href,
            'src': self.src,
            'rect': self.rect,
            'attributes': self.attributes
        }


class BrowserController:
    _cached_driver_path = None
    _cache_checked = False
    _shared_instance = None
    _shared_user_data_dir = None
    
    def __init__(self, browser_type: BrowserType = BrowserType.CHROME, use_shared: bool = True):
        self.browser_type = browser_type
        self.driver = None
        self.is_running = False
        self.use_shared = use_shared and browser_type == BrowserType.CHROME
    
    @classmethod
    def get_shared_user_data_dir(cls):
        if cls._shared_user_data_dir is None:
            import os
            app_data = os.path.join(os.path.expanduser("~"), ".rpa_yifei", "browser_data")
            os.makedirs(app_data, exist_ok=True)
            cls._shared_user_data_dir = app_data
        return cls._shared_user_data_dir
    
    @classmethod
    def get_shared_instance(cls):
        if cls._shared_instance is None or not cls._shared_instance.is_running:
            try:
                cls._shared_instance = cls(BrowserType.CHROME, use_shared=True)
                cls._shared_instance.start(
                    headless=False,
                    user_data_dir=cls.get_shared_user_data_dir()
                )
            except Exception as e:
                print(f"Failed to create shared browser instance: {e}")
                return None
        return cls._shared_instance
    
    @classmethod
    def close_shared_instance(cls):
        if cls._shared_instance:
            try:
                cls._shared_instance.close()
            except:
                pass
            cls._shared_instance = None
    
    @classmethod
    def connect_to_existing(cls, debug_port=9222):
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', debug_port))
            sock.close()
            
            if result != 0:
                return None
            
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            try:
                driver_path = cls._get_driver_path()
                service = Service(driver_path)
            except Exception as e:
                print(f"Failed to get driver path: {e}")
                return None
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(10)
            driver.implicitly_wait(2)
            _ = driver.current_url
            
            controller = cls(BrowserType.CHROME, use_shared=True)
            controller.driver = driver
            controller.is_running = True
            return controller
        except Exception as e:
            print(f"Failed to connect to existing browser: {e}")
            return None
    
    @classmethod
    def connect_to_existing_or_create(cls, debug_port=9222):
        existing = cls.connect_to_existing(debug_port)
        if existing:
            return existing
        
        return cls(BrowserType.CHROME, use_shared=True)
    
    @classmethod
    def _get_driver_path(cls):
        if cls._cached_driver_path and cls._cache_checked:
            return cls._cached_driver_path
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            import os
            
            driver_path = ChromeDriverManager().install()
            cls._cached_driver_path = driver_path
            cls._cache_checked = True
            
            os.environ['WDM_SSL_VERIFY'] = '0'
            
            return driver_path
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to get ChromeDriver: {e}")
            
            if cls._cached_driver_path and os.path.exists(cls._cached_driver_path):
                warnings.warn("Using cached ChromeDriver path")
                cls._cache_checked = True
                return cls._cached_driver_path
            
            return None
    
    def start(self, headless: bool = False, user_data_dir: Optional[str] = None):
        if self.is_running:
            return
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            if self.browser_type == BrowserType.CHROME:
                options = Options()
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-logging')
                options.add_argument('--log-level=3')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--ignore-ssl-errors')
                options.add_argument('--remote-debugging-port=9222')
                
                if not headless:
                    options.add_argument('--start-maximized')
                    options.add_argument('--disable-extensions')
                else:
                    options.add_argument('--headless=new')
                
                if self.use_shared:
                    effective_user_data_dir = user_data_dir or self.get_shared_user_data_dir()
                else:
                    effective_user_data_dir = user_data_dir
                
                if effective_user_data_dir:
                    options.add_argument(f'--user-data-dir={effective_user_data_dir}')
                
                options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                options.add_experimental_option('useAutomationExtension', False)
                
                driver_path = self._get_driver_path()
                if not driver_path:
                    raise Exception(
                        "无法获取ChromeDriver：\n"
                        "1. 请确保网络连接正常\n"
                        "2. 或者手动下载ChromeDriver并放到PATH中\n"
                        "3. 下载地址：https://chromedriver.chromium.org/downloads\n"
                        "   （注意选择与Chrome版本匹配的版本）"
                    )
                
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(10)
            
            elif self.browser_type == BrowserType.FIREFOX:
                options = None
                service = Service(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(15)
            
            elif self.browser_type == BrowserType.EDGE:
                options = None
                service = Service(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(15)
            self.is_running = True
            
        except ImportError:
            raise ImportError("Selenium is required. Install with: pip install selenium webdriver-manager")
    
    def navigate(self, url: str):
        if not self.driver:
            raise RuntimeError("Browser not started. Call start() first.")
        self.driver.get(url)
    
    def find_element_by_xpath(self, xpath: str):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        from selenium.webdriver.common.by import By
        return self.driver.find_element(By.XPATH, xpath)
    
    def find_element_by_css(self, css: str):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        from selenium.webdriver.common.by import By
        return self.driver.find_element(By.CSS_SELECTOR, css)
    
    def find_element_by_id(self, element_id: str):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        from selenium.webdriver.common.by import By
        return self.driver.find_element(By.ID, element_id)
    
    def get_all_elements(self) -> List:
        if not self.driver:
            raise RuntimeError("Browser not started.")
        return self.driver.find_elements('xpath', '//*')
    
    def click_element(self, locator: str, locator_type: str = 'xpath'):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        try:
            by = getattr(By, locator_type.upper(), By.XPATH)
            wait = WebDriverWait(self.driver, 10)
            element = wait.until(EC.element_to_be_clickable((by, locator)))
            element.click()
            return True
        except Exception as e:
            try:
                element = self._find_element(locator, locator_type)
                if element:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
            except:
                pass
            raise RuntimeError(f"无法点击元素: {str(e)}")
    
    def input_text(self, locator: str, text: str, locator_type: str = 'xpath'):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        try:
            by = getattr(By, locator_type.upper(), By.XPATH)
            wait = WebDriverWait(self.driver, 10)
            element = wait.until(EC.element_to_be_clickable((by, locator)))
            
            element.click()
            self.driver.execute_script("arguments[0].value = '';", element)
            element.send_keys(text)
            return True
        except Exception as e:
            try:
                element = self._find_element(locator, locator_type)
                if element:
                    self.driver.execute_script("arguments[0].value = '';", element)
                    element.send_keys(text)
                    return True
            except:
                pass
            raise RuntimeError(f"无法输入文本到元素: {str(e)}")
    
    def get_element_info(self, element) -> ElementInfo:
        from selenium.webdriver.common.by import By
        
        tag_name = element.tag_name
        element_id = element.get_attribute('id') or None
        name = element.get_attribute('name') or None
        class_name = element.get_attribute('class') or None
        text = element.text or None
        href = element.get_attribute('href') or None
        src = element.get_attribute('src') or None
        
        rect = element.rect
        attributes = self.driver.execute_script(
            "var items = {}; "
            "for (index = 0; index < arguments[0].attributes.length; ++index) { "
            "items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value; }; "
            "return items;", element
        )
        
        xpath = self._generate_xpath(element)
        css_selector = self._generate_css_selector(element)
        
        return ElementInfo(
            tag_name=tag_name,
            id=element_id,
            name=name,
            class_name=class_name,
            xpath=xpath,
            css_selector=css_selector,
            text=text,
            href=href,
            src=src,
            rect={'x': rect['x'], 'y': rect['y'], 'width': rect['width'], 'height': rect['height']},
            attributes=attributes
        )
    
    def _find_element(self, locator: str, locator_type: str):
        from selenium.webdriver.common.by import By
        by = getattr(By, locator_type.upper(), By.XPATH)
        return self.driver.find_element(by, locator)
    
    def _generate_xpath(self, element) -> str:
        return self.driver.execute_script("""
            function getUniqueXPath(element) {
                if (!element || !element.tagName) return '';
                
                // 1. 优先使用ID（最精确）
                if (element.id) {
                    return "//*[@id='" + element.id + "']";
                }
                
                // 2. 使用name属性
                var name = element.getAttribute('name');
                if (name) {
                    var tag = element.tagName.toLowerCase();
                    var nameCount = document.querySelectorAll(tag + '[name="' + name + '"]').length;
                    if (nameCount === 1) {
                        return "//" + tag + "[@name='" + name + "']";
                    }
                }
                
                // 3. 使用data-*属性
                var dataId = element.getAttribute('data-id');
                if (dataId) {
                    return "//*[@data-id='" + dataId + "']";
                }
                
                var dataTestId = element.getAttribute('data-testid');
                if (dataTestId) {
                    return "//*[@data-testid='" + dataTestId + "']";
                }
                
                var dataCy = element.getAttribute('data-cy');
                if (dataCy) {
                    return "//*[@data-cy='" + dataCy + "']";
                }
                
                // 4. 构建带父元素信息的路径
                var pathParts = [];
                var current = element;
                var maxDepth = 10;
                var depth = 0;
                
                while (current && current !== document.body && depth < maxDepth) {
                    var part = getElementXPathPart(current, depth);
                    if (part) {
                        pathParts.unshift(part);
                    }
                    current = current.parentNode;
                    depth++;
                }
                
                var xpath = '/html' + pathParts.join('');
                
                // 5. 验证XPath是否唯一，如果不唯一，尝试添加更多限定
                var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                
                if (matches.snapshotLength === 1) {
                    return xpath;
                }
                
                // 6. 如果不唯一，尝试使用class或其他属性
                var altXPath = getAlternativeXPath(element);
                if (altXPath) {
                    matches = document.evaluate(altXPath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return altXPath;
                    }
                }
                
                return xpath;
            }
            
            function getElementXPathPart(element, depth) {
                if (!element || !element.tagName || element.tagName === 'HTML') {
                    return '';
                }
                
                var tag = element.tagName.toLowerCase();
                
                // 跳过没有实际意义的包装元素
                var skipTags = ['tbody', 'thead', 'tfoot', 'colgroup'];
                if (skipTags.indexOf(tag) !== -1) {
                    return '';
                }
                
                var ix = 0;
                var siblings = element.parentNode ? element.parentNode.children : [];
                
                for (var i = 0; i < siblings.length; i++) {
                    if (siblings[i] === element) break;
                    if (siblings[i].tagName === element.tagName) ix++;
                }
                
                // 如果是唯一的子元素，不需要索引
                var sameTagSiblings = Array.from(siblings).filter(function(s) {
                    return s.tagName === element.tagName;
                });
                
                if (sameTagSiblings.length === 1) {
                    return '/' + tag;
                }
                
                return '/' + tag + '[' + (ix + 1) + ']';
            }
            
            function getAlternativeXPath(element) {
                var tag = element.tagName.toLowerCase();
                var className = element.className;
                var placeholder = element.getAttribute('placeholder');
                var type = element.getAttribute('type');
                var role = element.getAttribute('role');
                var ariaLabel = element.getAttribute('aria-label');
                var text = element.textContent.trim().substring(0, 50);
                
                // 优先使用：role + aria-label
                if (role && ariaLabel) {
                    var xpath = "//*[@role='" + role + "' and @aria-label='" + ariaLabel + "']";
                    var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return xpath;
                    }
                }
                
                // 使用：role + text
                if (role && text && text.length > 2) {
                    var xpath = "//*[@role='" + role + "' and contains(text(),'" + escapeXPathText(text) + "')]";
                    var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return xpath;
                    }
                }
                
                // 使用：input[type + placeholder]
                if (tag === 'input' && type && placeholder) {
                    var xpath = "//input[@type='" + type + "' and @placeholder='" + placeholder + "']";
                    var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return xpath;
                    }
                }
                
                // 使用：带有class的部分匹配
                if (className && typeof className === 'string') {
                    var classes = className.split(/\\s+/).filter(function(c) {
                        return c.length > 3 && !c.match(/^(active|hover|focus|disabled|selected)$/i);
                    });
                    
                    for (var i = 0; i < classes.length; i++) {
                        var cls = classes[i];
                        if (cls.length > 5) {
                            var xpath = "//*[contains(@class,'" + cls + "')]";
                            var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            if (matches.snapshotLength === 1) {
                                return xpath;
                            }
                            
                            // 尝试标签 + class组合
                            xpath = "//" + tag + "[contains(@class,'" + cls + "')]";
                            matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                            if (matches.snapshotLength === 1) {
                                return xpath;
                            }
                        }
                    }
                }
                
                // 使用：text内容定位
                if (text && text.length > 3 && text.length < 100) {
                    var xpath = "//*[contains(text(),'" + escapeXPathText(text) + "')]";
                    var matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return xpath;
                    }
                    
                    // 使用精确文本匹配
                    xpath = "//*[text()='" + escapeXPathText(text) + "']";
                    matches = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (matches.snapshotLength === 1) {
                        return xpath;
                    }
                }
                
                return null;
            }
            
            function escapeXPathText(text) {
                return text.replace(/'/g, \"'\").replace(/"/g, '\"');
            }
            
            return getUniqueXPath(arguments[0]);
        """, element)
    
    def _generate_css_selector(self, element) -> str:
        if element.id:
            return f"#{element.id}"
        return self.driver.execute_script("""
            function getUniqueCssSelector(el) {
                if (!el || !el.tagName) return '';
                
                // 1. 优先使用ID
                if (el.id) {
                    return '#' + el.id;
                }
                
                // 2. 使用name属性
                var name = el.getAttribute('name');
                if (name) {
                    var tag = el.tagName.toLowerCase();
                    return tag + '[name="' + name + '"]';
                }
                
                // 3. 构建路径
                var path = [];
                var current = el;
                var maxDepth = 10;
                var depth = 0;
                
                while (current && current !== document.body && depth < maxDepth) {
                    var tag = current.tagName ? current.tagName.toLowerCase() : '';
                    if (!tag || tag === 'html') break;
                    
                    var selector = getCssSelectorPart(current);
                    if (selector) {
                        path.unshift(selector);
                    }
                    
                    current = current.parentNode;
                    depth++;
                }
                
                var css = 'body > ' + path.join(' > ');
                
                // 4. 验证是否唯一
                try {
                    if (document.querySelectorAll(css).length === 1) {
                        return css;
                    }
                } catch (e) {}
                
                // 5. 尝试其他属性组合
                var altSelector = getAlternativeCssSelector(el);
                if (altSelector) {
                    try {
                        if (document.querySelectorAll(altSelector).length === 1) {
                            return altSelector;
                        }
                    } catch (e) {}
                }
                
                return css;
            }
            
            function getCssSelectorPart(el) {
                if (!el || !el.tagName) return '';
                
                var tag = el.tagName.toLowerCase();
                var classes = el.className && typeof el.className === 'string' 
                    ? el.className.split(/\\s+/).filter(function(c) {
                        return c.length > 2 && !c.match(/^(active|hover|focus|disabled|selected)$/i);
                    })
                    : [];
                
                if (classes.length > 0) {
                    // 使用第一个有意义的class
                    for (var i = 0; i < classes.length; i++) {
                        if (classes[i].length > 4) {
                            var clsSelector = '.' + classes[i];
                            var siblings = el.parentNode ? el.parentNode.querySelectorAll(clsSelector) : [];
                            if (siblings.length === 1) {
                                return tag + clsSelector;
                            }
                        }
                    }
                }
                
                // 使用nth-child
                var siblings = el.parentNode ? Array.from(el.parentNode.children) : [];
                var index = siblings.indexOf(el) + 1;
                
                // 如果同标签只有一个，不需要nth-child
                var sameTagSiblings = siblings.filter(function(s) {
                    return s.tagName === el.tagName;
                });
                
                if (sameTagSiblings.length === 1) {
                    return tag;
                }
                
                return tag + ':nth-child(' + index + ')';
            }
            
            function getAlternativeCssSelector(el) {
                var tag = el.tagName.toLowerCase();
                var classes = el.className && typeof el.className === 'string' 
                    ? el.className.split(/\\s+/).filter(function(c) {
                        return c.length > 4 && !c.match(/^(active|hover|focus|disabled|selected)$/i);
                    })
                    : [];
                
                var placeholder = el.getAttribute('placeholder');
                var type = el.getAttribute('type');
                var role = el.getAttribute('role');
                
                // 尝试：tag + class组合
                for (var i = 0; i < classes.length; i++) {
                    var selector = tag + '.' + classes[i];
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch (e) {}
                }
                
                // 尝试：tag[attribute]
                if (placeholder) {
                    var selector = tag + '[placeholder="' + placeholder + '"]';
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch (e) {}
                }
                
                if (type) {
                    var selector = tag + '[type="' + type + '"]';
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch (e) {}
                }
                
                if (role) {
                    var selector = '[role="' + role + '"]';
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch (e) {}
                }
                
                return null;
            }
            
            return getUniqueCssSelector(arguments[0]);
        """, element)
    
    def take_screenshot(self, path: Optional[str] = None) -> bytes:
        if not self.driver:
            raise RuntimeError("Browser not started.")
        return self.driver.get_screenshot_as_png()
    
    def get_page_source(self) -> str:
        if not self.driver:
            raise RuntimeError("Browser not started.")
        return self.driver.page_source
    
    def execute_script(self, script: str):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        return self.driver.execute_script(script)
    
    def wait_for_element(self, locator: str, locator_type: str = 'xpath', timeout: int = 30):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        by = getattr(By, locator_type.upper(), By.XPATH)
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, locator)))
    
    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_running = False
    
    def enable_pick_mode(self):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        
        script = """
        window.__selenium_element_picker = {
            highlighted_element: null,
            original_border: null,
            original_outline: null,
            ctrl_pressed: false,
            
            find_interactive_element: function(element) {
                if (!element) return null;
                
                if (['INPUT', 'TEXTAREA', 'SELECT'].indexOf(element.tagName) !== -1) {
                    return element;
                }
                
                if (element.contentEditable === 'true' || element.contentEditable === 'plaintext-only') {
                    return element;
                }
                
                var interactiveTags = ['INPUT', 'TEXTAREA', 'SELECT', 'A', 'BUTTON'];
                if (interactiveTags.indexOf(element.tagName) !== -1) {
                    return element;
                }
                
                var children = element.querySelectorAll('input, textarea, select, [contenteditable]');
                if (children.length > 0) {
                    for (var i = 0; i < children.length; i++) {
                        var child = children[i];
                        var rect = child.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return child;
                        }
                    }
                }
                
                return element;
            },
            
            highlight_element: function(element) {
                if (this.highlighted_element === element) return;
                this.remove_highlight();
                
                this.highlighted_element = element;
                this.original_border = element.style.border;
                this.original_outline = element.style.outline;
                
                element.style.border = '2px solid #0078D4';
                element.style.outline = '2px solid #0078D4';
                element.style.zIndex = '999999';
            },
            
            remove_highlight: function() {
                if (this.highlighted_element) {
                    this.highlighted_element.style.border = this.original_border || '';
                    this.highlighted_element.style.outline = this.original_outline || '';
                    this.highlighted_element.style.zIndex = '';
                    this.highlighted_element = null;
                }
            },
            
            get_element_at_point: function(x, y) {
                var element = document.elementFromPoint(x, y);
                if (!element) return null;
                
                var interactive = this.find_interactive_element(element);
                if (interactive && interactive !== element) {
                    return interactive;
                }
                
                var children = element.querySelectorAll('input, textarea, select');
                if (children.length > 0) {
                    for (var i = 0; i < children.length; i++) {
                        var child = children[i];
                        var rect = child.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && 
                            rect.x <= x && rect.x + rect.width >= x &&
                            rect.y <= y && rect.y + rect.height >= y) {
                            return child;
                        }
                    }
                }
                
                return element;
            }
        };
        
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey) {
                window.__selenium_element_picker.ctrl_pressed = true;
                document.body.style.cursor = 'crosshair';
            }
        });
        
        document.addEventListener('keyup', function(e) {
            if (!e.ctrlKey) {
                window.__selenium_element_picker.ctrl_pressed = false;
                document.body.style.cursor = '';
            }
        });
        
        document.addEventListener('mousemove', function(e) {
            var element = window.__selenium_element_picker.get_element_at_point(e.clientX, e.clientY);
            if (element) {
                window.__selenium_element_picker.highlight_element(element);
            }
        });
        
        document.addEventListener('click', function(e) {
            if (window.__selenium_element_picker.ctrl_pressed) {
                e.preventDefault();
                e.stopPropagation();
                var element = window.__selenium_element_picker.get_element_at_point(e.clientX, e.clientY);
                if (element) {
                    window.__selenium_last_clicked_element = element;
                }
                return false;
            }
        }, true);
        
        return 'Pick mode enabled - Hold Ctrl + Click to pick';
        """
        
        self.driver.execute_script(script)
    
    def disable_pick_mode(self):
        if not self.driver:
            return
        
        script = """
        if (window.__selenium_element_picker) {
            window.__selenium_element_picker.remove_highlight();
            delete window.__selenium_element_picker;
            delete window.__selenium_last_clicked_element;
        }
        document.body.style.cursor = '';
        """
        self.driver.execute_script(script)
    
    def get_element_at_position(self, x: int, y: int):
        if not self.driver:
            raise RuntimeError("Browser not started.")
        
        script = """
        var element = document.elementFromPoint(arguments[0], arguments[1]);
        if (element) {
            var rect = element.getBoundingClientRect();
            return {
                'tag': element.tagName.toLowerCase(),
                'id': element.id || '',
                'class': element.className || '',
                'text': element.innerText || '',
                'xpath': '',
                'rect': {
                    'x': rect.x,
                    'y': rect.y,
                    'width': rect.width,
                    'height': rect.height
                }
            };
        }
        return null;
        """
        
        result = self.driver.execute_script(script, x, y)
        return result
    
    def __del__(self):
        self.close()
