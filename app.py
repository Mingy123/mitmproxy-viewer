"""Application entry point for the mitmproxy flow viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mitmproxy.http import HTTPFlow
from textual.app import App

from pages.flow_list import FlowListScreen


class FlowViewerApp(App):
    """Textual application that orchestrates the available screens."""

    def __init__(self, *, flows: Sequence[HTTPFlow], source_path: Path) -> None:
        super().__init__()
        self._flows = flows
        self._source_path = source_path

    def on_mount(self) -> None:
        self.push_screen(FlowListScreen(self._flows, self._source_path))
