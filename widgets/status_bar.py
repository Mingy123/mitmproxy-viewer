"""Reusable widgets for the mitmproxy viewer application."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """Simple status bar docked to the bottom of the screen."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        background: $surface-darken-2;
        color: $text;
        padding: 0 1;
        height: 3;
        content-align: left middle;
    }
    """
