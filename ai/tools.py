"""Tool system for Orbit AI - bridges commands and provides typed tool interfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    data: dict[str, Any] | None = None


class ToolExecutor:
    """Executes tools by bridging to the shell's command registry."""
    
    def __init__(self, shell, command_metadata: list):
        self.shell = shell
        self.command_metadata = command_metadata
        self._command_map = {meta.name: meta for meta in command_metadata}
    
    def get_catalog(self) -> list[str]:
        """Generate compact command catalog for Orbit's system prompt."""
        lines = []
        for meta in self.command_metadata:
            aliases = f" [{', '.join(meta.aliases)}]" if meta.aliases else ""
            lines.append(f"{meta.name}{aliases}: {meta.description} | usage: {meta.usage}")
        return lines
    
    def run_command(self, name: str, args: list[str] | str = None) -> ToolResult:
        """
        Execute a RiftShell command using the EXACT same path as CLI.
        
        Args:
            name: Command name
            args: Arguments (list or space-separated string)
        
        Returns:
            ToolResult with success flag and output
        """
        if args is None:
            args = []
        elif isinstance(args, str):
            # Keep as string - shell.execute_line will parse it
            command_line = f"{name} {args}".strip()
        else:
            # Join list args
            command_line = f"{name} {' '.join(str(a) for a in args)}".strip()
        
        try:
            result = self.shell.execute_line(command_line)
            return ToolResult(
                success=result.success,
                output=result.output or "",
                data={"actions": result.actions} if result.actions else None
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"Command execution error: {e}"
            )
    
    # === Typed tools for rich browser/PC control ===
    
    def browser_goto(self, url: str) -> ToolResult:
        """Navigate browser to URL."""
        return self.run_command("browser", f"open {url}")
    
    def browser_search(self, query: str, engine: str = "Google") -> ToolResult:
        """Search using specified engine."""
        return self.run_command("browser", f"search {query} --engine {engine}")
    
    def browser_click(self, ref: str) -> ToolResult:
        """Click element by reference (e.g., e5) or text."""
        if ref.startswith('e') and ref[1:].isdigit():
            # Element reference - use existing click
            return self.run_command("browser", f"click {ref}")
        else:
            # Text match
            return self.run_command("browser", f"click {ref}")
    
    def browser_type(self, ref: str, text: str) -> ToolResult:
        """Type text into element."""
        return self.run_command("browser", f"fill {ref} {text}")
    
    def browser_press(self, key: str) -> ToolResult:
        """Press keyboard key in browser."""
        from utils.browser import get_browser_controller
        try:
            ctrl = get_browser_controller()
            return ToolResult(success=True, output=ctrl.press_key(key))
        except Exception as e:
            return ToolResult(success=False, output=f"Key press failed: {e}")
    
    def browser_scroll(self, direction: str = "down", amount: int = 500) -> ToolResult:
        """Scroll page."""
        if direction == "down":
            return self.run_command("browser", f"scrollpx {amount}")
        elif direction == "up":
            return self.run_command("browser", f"scrollpx -{amount}")
        else:
            return self.run_command("browser", f"control {direction}")
    
    def browser_snapshot(self) -> ToolResult:
        """Get current page DOM snapshot."""
        from utils.browser import get_browser_controller
        try:
            ctrl = get_browser_controller()
            dom = ctrl.get_current_dom()
            # Return compact version
            title = dom.get('title', '')
            url = dom.get('url', '')
            elements = dom.get('elements', [])
            
            # Compact format
            lines = [f"Page: {title}", f"URL: {url}", ""]
            
            # Group elements by viewport status if available
            in_view = [el for el in elements if el.get('in_view', True)]
            out_view = [el for el in elements if not el.get('in_view', True)]
            
            lines.append(f"Interactive elements in viewport ({len(in_view)}):")
            for el in in_view[:50]:  # Limit to 50 visible
                ref = el.get('ref', '')
                tag = el.get('tag', '')
                text = el.get('text', '')[:50]
                lines.append(f"  [{ref}] {tag} \"{text}\"")
            
            if out_view:
                lines.append(f"\n(+{len(out_view)} more elements below fold - scroll to view)")
            
            output = '\n'.join(lines)
            return ToolResult(success=True, output=output, data=dom)
        except Exception as e:
            return ToolResult(success=False, output=f"Snapshot failed: {e}")
    
    def browser_read_page_text(self) -> ToolResult:
        """Get page text content."""
        from utils.browser import get_browser_controller
        try:
            ctrl = get_browser_controller()
            dom = ctrl.get_current_dom()
            body = dom.get('body', '')
            return ToolResult(success=True, output=f"Page text:\n{body}")
        except Exception as e:
            return ToolResult(success=False, output=f"Read failed: {e}")
    
    def browser_back(self) -> ToolResult:
        """Navigate back."""
        return self.run_command("browser", "control back")
    
    def browser_tabs(self) -> ToolResult:
        """List open tabs."""
        return self.run_command("browser", "control tabs")
    
    def browser_close_tab(self) -> ToolResult:
        """Close current tab."""
        return self.run_command("browser", "control close_tab")
    
    # === PC Control tools ===
    
    def pc_windows_list(self) -> ToolResult:
        """List all open windows."""
        return self.run_command("pc", "windows list")
    
    def pc_windows_focus(self, title: str) -> ToolResult:
        """Focus window by title."""
        return self.run_command("pc", f"windows focus {title}")
    
    def pc_windows_minimize(self, title: str) -> ToolResult:
        """Minimize window."""
        return self.run_command("pc", f"windows minimize {title}")
    
    def pc_windows_maximize(self, title: str) -> ToolResult:
        """Maximize window."""
        return self.run_command("pc", f"windows maximize {title}")
    
    def pc_windows_close(self, title: str) -> ToolResult:
        """Close window."""
        return self.run_command("pc", f"windows close {title}")
    
    def pc_mouse_move(self, x: int, y: int) -> ToolResult:
        """Move mouse to coordinates."""
        return self.run_command("pc", f"mouse move {x} {y}")
    
    def pc_mouse_click(self, x: int = None, y: int = None) -> ToolResult:
        """Click mouse at position or current location."""
        if x is not None and y is not None:
            return self.run_command("pc", f"mouse click {x} {y}")
        return self.run_command("pc", "mouse click")
    
    def pc_mouse_scroll(self, amount: int) -> ToolResult:
        """Scroll mouse wheel (positive=up, negative=down)."""
        return self.run_command("pc", f"mouse scroll {amount}")
    
    def pc_keyboard_type(self, text: str) -> ToolResult:
        """Type text."""
        return self.run_command("pc", f"keyboard type {text}")
    
    def pc_keyboard_press(self, key: str) -> ToolResult:
        """Press a key."""
        return self.run_command("pc", f"keyboard press {key}")
    
    def pc_keyboard_hotkey(self, *keys: str) -> ToolResult:
        """Press hotkey combination (e.g., ctrl, c)."""
        keys_str = ' '.join(keys)
        return self.run_command("pc", f"keyboard hotkey {keys_str}")
    
    def pc_screen_capture(self, path: str = None) -> ToolResult:
        """Capture screenshot."""
        if path:
            return self.run_command("pc", f"screen capture {path}")
        return self.run_command("pc", "screen capture")
    
    def pc_screen_size(self) -> ToolResult:
        """Get screen resolution."""
        return self.run_command("pc", "screen size")


def create_tool_executor(shell, command_metadata: list) -> ToolExecutor:
    """Factory function to create a tool executor."""
    return ToolExecutor(shell, command_metadata)
