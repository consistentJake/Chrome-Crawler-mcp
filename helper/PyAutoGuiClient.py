"""
PyAutoGUI Client for Mouse and Keyboard Actions

IMPORTANT - macOS Accessibility Permissions:
============================================
This script uses PyAutoGUI which requires accessibility permissions on macOS.

Required Permissions:
1. Add "AEServer" to System Settings > Privacy & Security > Accessibility
2. Add "Terminal" to System Settings > Privacy & Security > Accessibility

Usage Options:
- Option A: Run in a standalone Terminal (not VS Code's integrated terminal)
- Option B: Add "Visual Studio Code" to the Accessibility list, then you can run in VS Code's terminal

Without these permissions, PyAutoGUI will fail silently or raise permission errors.
"""

import time
import random
import pyautogui
from typing import Dict, Any


class PyAutoGuiClient:
    """Client for performing mouse and keyboard actions using PyAutoGUI"""

    def __init__(self, scroll_amount: int = 3, scroll_pause: float = 0.1, jitter_range: tuple = (0.7, 1.3)):
        """
        Initialize the PyAutoGUI client.

        Args:
            scroll_amount: Number of scroll clicks per action (negative = down, positive = up)
            scroll_pause: Pause between scroll actions in seconds
            jitter_range: Tuple of (min, max) multipliers for random jitter (default: 0.7 to 1.3)
        """
        self.scroll_amount = scroll_amount
        self.scroll_pause = scroll_pause
        self.jitter_range = jitter_range
        # Disable PyAutoGUI fail-safe to prevent errors
        pyautogui.FAILSAFE = True

    def scroll_down(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll down the page using mouse wheel.

        Args:
            times: Number of times to scroll down
            amount: Number of scroll clicks per action (overrides default)

        Returns:
            Dict with status and results
        """
        scroll_clicks = -(amount if amount is not None else self.scroll_amount)
        results = []

        try:
            for i in range(times):
                # Scroll down (negative value)
                pyautogui.scroll(scroll_clicks)
                results.append({
                    "status": "success",
                    "action": "scroll_down",
                    "iteration": i + 1,
                    "scroll_amount": scroll_clicks
                })

                # Pause between scrolls with jitter
                if i < times - 1:  # Don't pause after the last scroll
                    jittered_pause = self.scroll_pause * random.uniform(*self.jitter_range)
                    time.sleep(jittered_pause)

            return {
                "status": "success",
                "message": f"Scrolled down {times} time(s)",
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll down: {str(e)}",
                "results": results
            }

    def scroll_up(self, times: int = 1, amount: int = None) -> Dict[str, Any]:
        """
        Scroll up the page using mouse wheel.

        Args:
            times: Number of times to scroll up
            amount: Number of scroll clicks per action (overrides default)

        Returns:
            Dict with status and results
        """
        scroll_clicks = amount if amount is not None else self.scroll_amount
        results = []

        try:
            for i in range(times):
                # Scroll up (positive value)
                pyautogui.scroll(scroll_clicks)
                results.append({
                    "status": "success",
                    "action": "scroll_up",
                    "iteration": i + 1,
                    "scroll_amount": scroll_clicks
                })

                # Pause between scrolls with jitter
                if i < times - 1:  # Don't pause after the last scroll
                    jittered_pause = self.scroll_pause * random.uniform(*self.jitter_range)
                    time.sleep(jittered_pause)

            return {
                "status": "success",
                "message": f"Scrolled up {times} time(s)",
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to scroll up: {str(e)}",
                "results": results
            }

    def scroll_to_position(self, x: int, y: int) -> Dict[str, Any]:
        """
        Move mouse to a specific position (helper method for positioning before scroll).

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Dict with status
        """
        try:
            pyautogui.moveTo(x, y)
            return {
                "status": "success",
                "message": f"Moved mouse to ({x}, {y})"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to move mouse: {str(e)}"
            }

    def get_screen_size(self) -> Dict[str, Any]:
        """
        Get the current screen size.

        Returns:
            Dict with width and height
        """
        try:
            width, height = pyautogui.size()
            return {
                "status": "success",
                "width": width,
                "height": height
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get screen size: {str(e)}"
            }

    def close(self):
        """Close the client (placeholder for consistency with other clients)"""
        pass
