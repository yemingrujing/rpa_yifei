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
            raise
    
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
                
                service = Service(self._get_driver_path())
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
        return self.driver.execute_script(
            "function getXPath(element) {"
            "    if (element.id) return \"//*[@id='\" + element.id + \"']\";"
            "    if (element === document.body) return '/html' + getTagName(element);"
            "    var ix = 0;"
            "    var siblings = element.parentNode.childNodes;"
            "    for (var i = 0; i < siblings.length; i++) {"
            "        var sibling = siblings[i];"
            "        if (sibling === element) {"
            "            return getXPath(element.parentNode) + '/' + getTagName(element) + '[' + (ix + 1) + ']';"
            "        }"
            "        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {"
            "            ix++;"
            "        }"
            "    }"
            "}"
            "function getTagName(element) {"
            "    return element.tagName.toLowerCase();"
            "}"
            "return getXPath(arguments[0]);",
            element
        )
    
    def _generate_css_selector(self, element) -> str:
        if element.id:
            return f"#{element.id}"
        return self.driver.execute_script(
            "function getCssSelector(el) {"
            "    if (el.id) return '#' + el.id;"
            "    if (el === document.body) return 'body';"
            "    var parent = el.parentNode;"
            "    var siblings = Array.from(parent.children);"
            "    var index = siblings.indexOf(el) + 1;"
            "    return getCssSelector(parent) + ' > ' + el.tagName.toLowerCase() + ':nth-child(' + index + ')';"
            "}"
            "return getCssSelector(arguments[0]);",
            element
        )
    
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
