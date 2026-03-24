import time
import json
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
import numpy as np
import pyautogui


class ElementLocator:
    def __init__(self, gui_automation=None):
        self.gui = gui_automation
        self.locator_cache = {}

    def locate_by_image(self, image_path: str, confidence: float = 0.8, 
                       timeout: int = 30) -> Optional[Tuple[int, int, int, int]]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                target = Image.open(image_path)
                location = pyautogui.locateOnScreen(target, confidence=confidence)
                if location:
                    return (location.left, location.top, location.width, location.height)
            except Exception:
                pass
            time.sleep(0.3)
        return None

    def locate_by_image_region(self, image_path: str, region: Tuple[int, int, int, int],
                               confidence: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        try:
            target = Image.open(image_path)
            screenshot = self.gui.take_screenshot(region)
            result = pyautogui.locate(target, screenshot, confidence=confidence)
            if result:
                return (region[0] + result.left, region[1] + result.top, result.width, result.height)
        except Exception:
            pass
        return None

    def locate_all_by_image(self, image_path: str, confidence: float = 0.8) -> List[Tuple[int, int, int, int]]:
        try:
            target = Image.open(image_path)
            locations = list(pyautogui.locateAllOnScreen(target, confidence=confidence))
            return [(loc.left, loc.top, loc.width, loc.height) for loc in locations]
        except Exception:
            return []

    def locate_by_color(self, color: Tuple[int, int, int], tolerance: int = 10,
                       region: Optional[Tuple[int, int, int, int]] = None) -> List[Tuple[int, int]]:
        pixels = []
        screenshot = self.gui.take_screenshot(region)
        img_array = np.array(screenshot)
        
        if region:
            offset_x, offset_y = region[0], region[1]
        else:
            offset_x, offset_y = 0, 0
            
        for y in range(img_array.shape[0]):
            for x in range(img_array.shape[1]):
                pixel = img_array[y, x]
                if all(abs(int(pixel[i]) - color[i]) <= tolerance for i in range(3)):
                    pixels.append((x + offset_x, y + offset_y))
        return pixels

    def locate_by_template_match(self, template_path: str, threshold: float = 0.8) -> Optional[Tuple[float, int, int]]:
        try:
            template = Image.open(template_path)
            template_array = np.array(template)
            
            screenshot = self.gui.take_screenshot()
            screenshot_array = np.array(screenshot)
            
            if len(template_array.shape) == 3:
                template_gray = np.mean(template_array, axis=2)
                screenshot_gray = np.mean(screenshot_array, axis=2)
            else:
                template_gray = template_array
                screenshot_gray = screenshot_array
            
            from scipy.signal import correlate2d
            correlation = correlate2d(screenshot_gray, template_gray, mode='same')
            
            max_val = np.max(correlation)
            if max_val / (np.sum(template_gray) + 1e-6) >= threshold:
                max_pos = np.unravel_index(np.argmax(correlation), correlation.shape)
                template_h, template_w = template_array.shape[:2]
                return (max_val, max_pos[1] - template_w // 2, max_pos[0] - template_h // 2)
        except Exception:
            pass
        return None

    def get_element_center(self, location: Tuple[int, int, int, int]) -> Tuple[int, int]:
        x, y, w, h = location
        return (x + w // 2, y + h // 2)

    def create_locator_config(self, element_type: str, value: str, **kwargs) -> Dict[str, Any]:
        return {
            'type': element_type,
            'value': value,
            'timeout': kwargs.get('timeout', 30),
            'confidence': kwargs.get('confidence', 0.8),
            'region': kwargs.get('region'),
            'index': kwargs.get('index', 0)
        }

    def find_element(self, locator_config: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
        element_type = locator_config.get('type')
        value = locator_config.get('value')
        timeout = locator_config.get('timeout', 30)
        
        if element_type == 'image':
            return self.locate_by_image(value, locator_config.get('confidence', 0.8), timeout)
        elif element_type == 'color':
            color = eval(value)
            pixels = self.locate_by_color(color, locator_config.get('tolerance', 10))
            if pixels:
                idx = locator_config.get('index', 0)
                if idx < len(pixels):
                    return (pixels[idx][0], pixels[idx][1], 1, 1)
        elif element_type == 'position':
            x, y = map(int, value.split(','))
            return (x, y, 1, 1)
        
        return None

    def wait_for_element(self, locator_config: Dict[str, Any]) -> bool:
        timeout = locator_config.get('timeout', 30)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_element(locator_config):
                return True
            time.sleep(0.3)
        return False

    def click_element(self, locator_config: Dict[str, Any]) -> bool:
        location = self.find_element(locator_config)
        if location:
            center = self.get_element_center(location)
            self.gui.click(center[0], center[1])
            return True
        return False

    def highlight_element(self, locator_config: Dict[str, Any], duration: float = 2):
        location = self.find_element(locator_config)
        if location:
            x, y, w, h = location
            self.draw_rectangle(x, y, w, h, duration=duration)

    def draw_rectangle(self, x: int, y: int, w: int, h: int, duration: float = 2):
        import cv2
        import numpy as np
        
        times = int(duration / 0.1)
        for _ in range(times):
            screenshot = self.gui.take_screenshot()
            img_array = np.array(screenshot)
            
            cv2.rectangle(img_array, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            temp_path = f"_temp_highlight_{int(time.time())}.png"
            Image.fromarray(img_array).save(temp_path)
            
            time.sleep(0.1)
            
            try:
                import os
                os.remove(temp_path)
            except:
                pass

    def save_locator_config(self, config: Dict[str, Any], file_path: str):
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)

    def load_locator_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
