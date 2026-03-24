import pyautogui
import pygetwindow as gw
import time
import json
import os
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image
import numpy as np


class GUIAutomation:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.timeout = self.config.get('default_timeout', 30)
        self.click_interval = self.config.get('click_interval', 0.1)
        self.screenshot_quality = self.config.get('screenshot_quality', 80)
        pyautogui.PAUSE = self.click_interval
        pyautogui.FAILSAFE = True

    def get_screen_size(self) -> Tuple[int, int]:
        return pyautogui.size()

    def get_current_mouse_position(self) -> Tuple[int, int]:
        return pyautogui.position()

    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1, duration: float = 0):
        pyautogui.click(x, y, clicks=clicks, button=button, duration=duration)

    def right_click(self, x: int, y: int):
        pyautogui.click(x, y, button='right')

    def double_click(self, x: int, y: int):
        pyautogui.doubleClick(x, y)

    def move_to(self, x: int, y: int, duration: float = 0):
        pyautogui.moveTo(x, y, duration=duration)

    def drag_to(self, x: int, y: int, duration: float = 0.5, button: str = 'left'):
        pyautogui.dragTo(x, y, duration=duration, button=button)

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None):
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x, y)
        else:
            pyautogui.scroll(clicks)

    def type_text(self, text: str, interval: float = 0.05):
        pyautogui.write(text, interval=interval)

    def press_key(self, key: str):
        pyautogui.press(key)

    def hotkey(self, *keys):
        pyautogui.hold(keys[0])
        for key in keys[1:]:
            pyautogui.press(key)
        pyautogui.release(keys[0])

    def key_down(self, key: str):
        pyautogui.keyDown(key)

    def key_up(self, key: str):
        pyautogui.keyUp(key)

    def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        import mss
        with mss.mss() as sct:
            if region:
                monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
            else:
                monitor = sct.monitors[1]
            img = sct.grab(monitor)
            return Image.frombytes('RGB', img.size, img.rgb)

    def save_screenshot(self, path: str, region: Optional[Tuple[int, int, int, int]] = None):
        screenshot = self.take_screenshot(region)
        screenshot.save(path, quality=self.screenshot_quality)

    def find_image_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        try:
            target = Image.open(image_path)
            location = pyautogui.locateOnScreen(target, confidence=confidence)
            if location:
                return (location.left, location.top, location.width, location.height)
            return None
        except Exception:
            return None

    def find_all_images(self, image_path: str, confidence: float = 0.8) -> List[Tuple[int, int, int, int]]:
        try:
            target = Image.open(image_path)
            locations = list(pyautogui.locateAllOnScreen(target, confidence=confidence))
            return [(loc.left, loc.top, loc.width, loc.height) for loc in locations]
        except Exception:
            return []

    def click_image(self, image_path: str, confidence: float = 0.8, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            location = self.find_image_on_screen(image_path, confidence)
            if location:
                center_x = location[0] + location[2] // 2
                center_y = location[1] + location[3] // 2
                self.click(center_x, center_y)
                return True
            time.sleep(0.5)
        return False

    def get_window_list(self) -> List[Dict[str, Any]]:
        windows = gw.getAllWindows()
        return [
            {
                'title': w.title,
                'handle': w._hWnd,
                'visible': w.visible,
                'maximized': w.maximized,
                'minimized': w.minimized
            }
            for w in windows if w.title
        ]

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        try:
            w = gw.getActiveWindow()
            if w:
                return {
                    'title': w.title,
                    'handle': w._hWnd,
                    'visible': w.visible,
                    'maximized': w.maximized,
                    'minimized': w.minimized
                }
        except Exception:
            pass
        return None

    def activate_window(self, title: str) -> bool:
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return True
        except Exception:
            pass
        return False

    def get_window_rect(self, title: str) -> Optional[Tuple[int, int, int, int]]:
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                w = windows[0]
                return (w.left, w.top, w.width, w.height)
        except Exception:
            pass
        return None

    def focus_window(self, title: str) -> bool:
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].focus()
                return True
        except Exception:
            pass
        return False

    def wait_for_image(self, image_path: str, confidence: float = 0.8, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_image_on_screen(image_path, confidence):
                return True
            time.sleep(0.5)
        return False

    def wait_for_window(self, title: str, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if gw.getWindowsWithTitle(title):
                return True
            time.sleep(0.5)
        return False

    def get_color_at_position(self, x: int, y: int) -> Tuple[int, int, int]:
        screenshot = self.take_screenshot()
        pixel = screenshot.getpixel((x, y))
        return pixel

    def pixel_match_color(self, x: int, y: int, target_color: Tuple[int, int, int], tolerance: int = 10) -> bool:
        current_color = self.get_color_at_position(x, y)
        return all(abs(current_color[i] - target_color[i]) <= tolerance for i in range(3))

    def wait_for_pixel_color(self, x: int, y: int, target_color: Tuple[int, int, int], 
                             tolerance: int = 10, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.pixel_match_color(x, y, target_color, tolerance):
                return True
            time.sleep(0.2)
        return False
