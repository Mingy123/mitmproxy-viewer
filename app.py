"""Application entry point for the mitmproxy flow viewer."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mitmproxy.http import HTTPFlow
from textual.app import App

from flows import filter_flows_by_content_type
from pages.flow_list import FlowListScreen


class FlowViewerApp(App):
    """Textual application that orchestrates the available screens."""

    def __init__(
        self,
        *,
        flows: Sequence[HTTPFlow],
        source_path: Path,
        content_type_filter: str | None = None,
    ) -> None:
        super().__init__()
        self._all_flows = list(flows)
        self._source_path = source_path
        self._content_type_filter = content_type_filter
        self._filtered_flows: list[HTTPFlow] = []
        self._flow_list_screen: FlowListScreen | None = None

    def on_mount(self) -> None:
        self._filtered_flows = self._apply_content_type_filter()
        screen = FlowListScreen(
            flows=self._filtered_flows,
            source_path=self._source_path,
            content_type_filter=self._content_type_filter,
        )
        self._flow_list_screen = screen
        self.push_screen(screen)

    def _apply_content_type_filter(self) -> list[HTTPFlow]:
        flows: list[HTTPFlow] = list(self._all_flows)
        if self._content_type_filter:
            flows = filter_flows_by_content_type(flows, self._content_type_filter)
        return flows

    def set_content_type_filter(
        self,
        value: str | None,
        *,
        status_message: str | None = None,
    ) -> None:
        normalized = value.strip() if value and value.strip() else None
        if normalized == self._content_type_filter:
            if self._flow_list_screen and status_message is not None:
                self._flow_list_screen.update_flows(
                    self._filtered_flows,
                    self._content_type_filter,
                    status_message=status_message,
                )
            return

        self._content_type_filter = normalized
        self._filtered_flows = self._apply_content_type_filter()
        if self._flow_list_screen:
            self._flow_list_screen.update_flows(
                self._filtered_flows,
                self._content_type_filter,
                status_message=status_message,
            )

    def get_content_type_filter(self) -> str | None:
        return self._content_type_filter

    def get_flows(self) -> Sequence[HTTPFlow]:
        return list(self._filtered_flows)

    def focus_flow_in_list(self, index: int) -> None:
        if self._flow_list_screen is None:
            return
        self._flow_list_screen.focus_flow(index)
