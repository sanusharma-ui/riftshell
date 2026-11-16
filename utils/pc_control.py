"""Advanced PC control utilities for mouse, keyboard, windows, and screen."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional
import win32gui
import win32con
import win32api
import win32process
import pyautogui
import psutil
import win32clipboard


@dataclass
class WindowInfo:
    """Information about a window."""
    hwnd: int
    title: str
    class_name: str
    pid: int
    is_visible: bool
    is_minimized: bool
    is_maximized: bool
    rect: tuple[int, int, int, int]  # (left, top, right, bottom)
    process_name: str


class PCControlError(RuntimeError):
    """Raised when a PC control operation fails."""
    pass


class WindowController:
    """Control and manage Windows windows."""
    
    @staticmethod
    def list_windows(visible_only: bool = True, include_system: bool = False) -> list[WindowInfo]:
        """List all windows."""
        windows = []
        
        def callback(hwnd, _):
            if not win32gui.IsWindow(hwnd):
                return True
            
            is_visible = win32gui.IsWindowVisible(hwnd)
            if visible_only and not is_visible:
                return True
            
            title = win32gui.GetWindowText(hwnd)
            if not title and not include_system:
                return True
            
            class_name = win32gui.GetClassName(hwnd)
            
            # Skip some system windows, but never ApplicationFrameWindow (needed for UWP apps like Calculator)
            if not include_system and class_name in {"Windows.UI.Core.CoreWindow", "Shell_TrayWnd", "Progman"}:
                return True

            # For UWP apps, title might be on a child window
            if class_name == "ApplicationFrameWindow" and not title:
                def child_cb(chwnd, _):
                    nonlocal title
                    ct = win32gui.GetWindowText(chwnd)
                    if ct:
                        title = ct
                        return False
                    return True
                try:
                    win32gui.EnumChildWindows(hwnd, child_cb, None)
                except Exception:
                    pass
            
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                process_name = process.name()
            except Exception:
                pid = 0
                process_name = "Unknown"
            
            placement = win32gui.GetWindowPlacement(hwnd)
            is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED
            
            rect = win32gui.GetWindowRect(hwnd)
            
            windows.append(WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                pid=pid,
                is_visible=is_visible,
                is_minimized=is_minimized,
                is_maximized=is_maximized,
                rect=rect,
                process_name=process_name
            ))
            return True
        
        win32gui.EnumWindows(callback, None)
        return windows
    
    @staticmethod
    def find_window(title_contains: str = None, process_name: str = None) -> Optional[WindowInfo]:
        """Find a window by title or process name."""
        windows = WindowController.list_windows()
        
        if title_contains:
            title_lower = title_contains.lower()
            for window in windows:
                if title_lower in window.title.lower():
                    return window
        
        if process_name:
            process_lower = process_name.lower()
            for window in windows:
                if process_lower in window.process_name.lower():
                    return window
        
        return None
    
    @staticmethod
    def focus_window(hwnd: int) -> bool:
        """Bring a window to the foreground."""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            foreground = win32gui.GetForegroundWindow()
            current_thread = win32api.GetCurrentThreadId()
            target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
            foreground_thread = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else 0
            attached = False
            try:
                if foreground_thread and foreground_thread != current_thread:
                    win32api.AttachThreadInput(current_thread, foreground_thread, True)
                    attached = True
                if target_thread != current_thread:
                    win32api.AttachThreadInput(current_thread, target_thread, True)
                    attached = True
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetFocus(hwnd)
                return win32gui.GetForegroundWindow() == hwnd
            finally:
                if attached:
                    for thread_id in {foreground_thread, target_thread}:
                        if thread_id and thread_id != current_thread:
                            try:
                                win32api.AttachThreadInput(current_thread, thread_id, False)
                            except Exception:
                                pass
        except Exception:
            return False
    
    @staticmethod
    def minimize_window(hwnd: int) -> bool:
        """Minimize a window."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            return False
    
    @staticmethod
    def maximize_window(hwnd: int) -> bool:
        """Maximize a window."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception:
            return False
    
    @staticmethod
    def close_window(hwnd: int) -> bool:
        """Close a window gracefully."""
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_active_window() -> Optional[WindowInfo]:
        """Get the currently active window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                windows = WindowController.list_windows(visible_only=False)
                for window in windows:
                    if window.hwnd == hwnd:
                        return window
        except Exception:
            pass
        return None


class MouseController:
    """Control mouse movements and clicks."""
    
    # Safety: Disable PyAutoGUI fail-safe in controlled environment
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.1
    
    @staticmethod
    def get_position() -> tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()
    
    @staticmethod
    def move_to(x: int, y: int, duration: float = 0.2):
        """Move mouse to absolute position."""
        pyautogui.moveTo(x, y, duration=duration)
    
    @staticmethod
    def move_relative(x: int, y: int, duration: float = 0.2):
        """Move mouse relative to current position."""
        pyautogui.moveRel(x, y, duration=duration)
    
    @staticmethod
    def click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1):
        """Click at position (or current position if None)."""
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
    
    @staticmethod
    def double_click(x: Optional[int] = None, y: Optional[int] = None):
        """Double click at position."""
        MouseController.click(x, y, clicks=2)
    
    @staticmethod
    def right_click(x: Optional[int] = None, y: Optional[int] = None):
        """Right click at position."""
        MouseController.click(x, y, button="right")
    
    @staticmethod
    def scroll(clicks: int):
        """Scroll mouse wheel. Positive = up, negative = down."""
        pyautogui.scroll(clicks)
    
    @staticmethod
    def drag_to(x: int, y: int, duration: float = 0.5, button: str = "left"):
        """Drag mouse to position."""
        pyautogui.drag(x, y, duration=duration, button=button)


class KeyboardController:
    """Control keyboard input."""
    
    @staticmethod
    def type_text(text: str, interval: float = 0.05):
        """Type text with interval between keys, falling back to clipboard paste for non-ASCII/Hindi."""
        if not text:
            return
        if text.isascii():
            try:
                pyautogui.write(text, interval=interval)
                return
            except Exception:
                pass
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return
        except Exception:
            pass
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
            pyautogui.hotkey("ctrl", "v")
        except Exception as exc:
            raise PCControlError(f"Typing text failed: {exc}")
    
    @staticmethod
    def press_key(key: str):
        """Press and release a single key."""
        pyautogui.press(key)
    
    @staticmethod
    def hotkey(*keys):
        """Press multiple keys together (e.g., 'ctrl', 'c')."""
        pyautogui.hotkey(*keys)
    
    @staticmethod
    def press_and_hold(key: str):
        """Press down a key (must call release_key later)."""
        pyautogui.keyDown(key)
    
    @staticmethod
    def release_key(key: str):
        """Release a key."""
        pyautogui.keyUp(key)
    
    @staticmethod
    def enter():
        """Press Enter key."""
        KeyboardController.press_key('enter')
    
    @staticmethod
    def tab(count: int = 1):
        """Press Tab key one or more times."""
        for _ in range(count):
            KeyboardController.press_key('tab')
    
    @staticmethod
    def escape():
        """Press Escape key."""
        KeyboardController.press_key('escape')
    
    @staticmethod
    def backspace(count: int = 1):
        """Press Backspace key one or more times."""
        for _ in range(count):
            KeyboardController.press_key('backspace')


class ScreenController:
    """Screen capture and analysis utilities."""
    
    @staticmethod
    def get_screen_size() -> tuple[int, int]:
        """Get screen resolution."""
        return pyautogui.size()
    
    @staticmethod
    def take_screenshot(region: tuple[int, int, int, int] = None) -> pyautogui.Image:
        """
        Take a screenshot.
        region: (left, top, width, height) or None for full screen
        """
        return pyautogui.screenshot(region=region)
    
    @staticmethod
    def find_on_screen(image_path: str, confidence: float = 0.8) -> Optional[tuple[int, int]]:
        """
        Find an image on screen and return its center coordinates.
        Returns None if not found.
        """
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return pyautogui.center(location)
        except Exception:
            pass
        return None
    
    @staticmethod
    def click_image(image_path: str, confidence: float = 0.8) -> bool:
        """Find and click an image on screen."""
        location = ScreenController.find_on_screen(image_path, confidence)
        if location:
            MouseController.click(*location)
            return True
        return False
    
    @staticmethod
    def get_pixel_color(x: int, y: int) -> tuple[int, int, int]:
        """Get RGB color of pixel at position."""
        return pyautogui.pixel(x, y)


def execute_pc_command(command: str, *args) -> str:
    """
    Execute a PC control command.
    """
    flat_args = []
    for a in args:
        if isinstance(a, (list, tuple)):
            flat_args.extend(str(item) for item in a)
        elif a is not None:
            flat_args.append(str(a))
    args = flat_args
    
    if command == "windows":
        if not args:
            raise PCControlError("Usage: windows <list|focus|minimize|maximize|close> [title]")
        
        sub = args[0].lower()
        
        if sub == "list":
            windows = WindowController.list_windows()
            if not windows:
                return "No windows found."
            
            lines = ["Open windows:"]
            for i, win in enumerate(windows[:20], 1):
                status = []
                if win.is_minimized:
                    status.append("minimized")
                if win.is_maximized:
                    status.append("maximized")
                status_str = f" [{', '.join(status)}]" if status else ""
                lines.append(f"{i}. {win.title[:60]}{status_str} - {win.process_name}")
            return "\n".join(lines)
        
        elif sub in {"focus", "minimize", "maximize", "close"}:
            if len(args) < 2:
                raise PCControlError(f"Usage: windows {sub} <window_title>")
            
            title = " ".join(args[1:])
            window = WindowController.find_window(title_contains=title)
            
            if not window:
                raise PCControlError(f"Window not found: {title}")
            
            if sub == "focus":
                success = WindowController.focus_window(window.hwnd)
                return f"Focused: {window.title}" if success else f"Failed to focus: {window.title}"
            elif sub == "minimize":
                success = WindowController.minimize_window(window.hwnd)
                return f"Minimized: {window.title}" if success else f"Failed to minimize: {window.title}"
            elif sub == "maximize":
                success = WindowController.maximize_window(window.hwnd)
                return f"Maximized: {window.title}" if success else f"Failed to maximize: {window.title}"
            elif sub == "close":
                success = WindowController.close_window(window.hwnd)
                return f"Closed: {window.title}" if success else f"Failed to close: {window.title}"
            else:
                raise PCControlError(f"Unknown windows subcommand: {sub}")
        else:
            raise PCControlError(f"Unknown windows subcommand: {sub}")
    
    elif command == "mouse":
        if not args:
            raise PCControlError("Usage: mouse <move|click|scroll|position>")
        
        sub = args[0].lower()
        
        if sub == "position":
            x, y = MouseController.get_position()
            return f"Mouse position: ({x}, {y})"
        
        elif sub == "move":
            if len(args) < 3:
                raise PCControlError("Usage: mouse move <x> <y>")
            try:
                x, y = int(args[1]), int(args[2])
                MouseController.move_to(x, y)
                return f"Moved mouse to ({x}, {y})"
            except ValueError:
                raise PCControlError("Coordinates must be integers")
        
        elif sub in {"click", "left_click"}:
            if len(args) == 1:
                MouseController.click()
                x, y = MouseController.get_position()
                return f"Clicked at current position ({x}, {y})"
            elif len(args) == 2 and str(args[1]).lower() in {"center", "centre", "middle"}:
                width, height = ScreenController.get_screen_size()
                x, y = width // 2, height // 2
                MouseController.click(x, y)
                return f"Clicked at center of screen ({x}, {y})"
            elif len(args) >= 3:
                try:
                    x, y = int(args[1]), int(args[2])
                    MouseController.click(x, y)
                    return f"Clicked at ({x}, {y})"
                except ValueError:
                    raise PCControlError("Coordinates must be integers")
            else:
                raise PCControlError("Usage: mouse click [x y | center]")

        elif sub in {"double_click", "doubleclick"}:
            if len(args) == 1:
                MouseController.double_click()
                x, y = MouseController.get_position()
                return f"Double-clicked at ({x}, {y})"
            elif len(args) >= 3:
                x, y = int(args[1]), int(args[2])
                MouseController.double_click(x, y)
                return f"Double-clicked at ({x}, {y})"
            else:
                raise PCControlError("Usage: mouse double_click [x y]")

        elif sub in {"right_click", "rightclick"}:
            if len(args) == 1:
                MouseController.right_click()
                x, y = MouseController.get_position()
                return f"Right-clicked at ({x}, {y})"
            elif len(args) >= 3:
                x, y = int(args[1]), int(args[2])
                MouseController.right_click(x, y)
                return f"Right-clicked at ({x}, {y})"
            else:
                raise PCControlError("Usage: mouse right_click [x y]")
        
        elif sub == "scroll":
            if len(args) < 2:
                raise PCControlError("Usage: mouse scroll <amount>")
            try:
                amount = int(args[1])
                MouseController.scroll(amount)
                direction = "up" if amount > 0 else "down"
                return f"Scrolled {direction} by {abs(amount)} clicks"
            except ValueError:
                raise PCControlError("Scroll amount must be an integer")
        else:
            raise PCControlError(f"Unknown mouse subcommand: {sub}")
    
    elif command == "keyboard":
        if not args:
            raise PCControlError("Usage: keyboard <type|press|hotkey|enter|tab|escape>")
        
        sub = args[0].lower()
        
        if sub == "type":
            if len(args) < 2:
                raise PCControlError("Usage: keyboard type <text>")
            text = " ".join(args[1:])
            KeyboardController.type_text(text)
            return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        
        elif sub == "press":
            if len(args) < 2:
                raise PCControlError("Usage: keyboard press <key>")
            key = args[1]
            KeyboardController.press_key(key)
            return f"Pressed key: {key}"
        
        elif sub == "hotkey":
            if len(args) < 2:
                raise PCControlError("Usage: keyboard hotkey <key1> [key2] ...")
            keys = args[1:]
            KeyboardController.hotkey(*keys)
            return f"Pressed hotkey: {' + '.join(keys)}"
        
        elif sub == "enter":
            KeyboardController.enter()
            return "Pressed Enter"
        
        elif sub == "tab":
            count = int(args[1]) if len(args) > 1 else 1
            KeyboardController.tab(count)
            return f"Pressed Tab {count} time(s)"
        
        elif sub == "escape":
            KeyboardController.escape()
            return "Pressed Escape"
        else:
            raise PCControlError(f"Unknown keyboard subcommand: {sub}")
    
    elif command == "screen":
        if not args:
            raise PCControlError("Usage: screen <size|capture>")
        
        sub = args[0].lower()
        
        if sub == "size":
            width, height = ScreenController.get_screen_size()
            return f"Screen size: {width}x{height}"
        
        elif sub == "capture":
            import tempfile
            from pathlib import Path
            
            if len(args) > 1:
                path = Path(args[1])
            else:
                path = Path(tempfile.gettempdir()) / f"screenshot_{int(time.time())}.png"
            
            screenshot = ScreenController.take_screenshot()
            screenshot.save(str(path))
            return f"Screenshot saved: {path}"
        else:
            raise PCControlError(f"Unknown screen subcommand: {sub}")
    
    else:
        raise PCControlError(f"Unknown command: {command}")

    raise PCControlError(f"Unknown {command} subcommand: {args[0] if args else '(missing)'}")


def release_all_keys() -> None:
    """Release modifiers after an emergency stop."""
    for key in ("ctrl", "alt", "shift", "win"):
        try:
            pyautogui.keyUp(key)
        except Exception:
            pass
