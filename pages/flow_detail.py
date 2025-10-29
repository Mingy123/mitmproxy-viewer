"""Detail page that shows information about a single HTTP flow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rich.text import Text
from mitmproxy.http import HTTPFlow
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static

from widgets.status_bar import StatusBar


class FlowDetailScreen(Screen):
    """Screen that renders request and response details for a flow."""

    CSS = """
    FlowDetailScreen {
        layout: vertical;
    }

    #detail-container {
        height: 1fr;
        padding: 1;
        layout: vertical;
    }

    #request-container,
    #response-container {
        height: 1fr;
    }

    #request-detail,
    #response-detail {
        padding: 1;
        border: solid $surface;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("backspace", "go_back", "Back"),
        ("q", "app.quit", "Quit"),
        ("tab", "cycle_detail_panel", "Switch Request/Response"),
    ]

    def __init__(self, *, flow: HTTPFlow, position: int, total: int, source_path: Path) -> None:
        super().__init__()
        self._flow = flow
        self._position = position
        self._total = total
        self._source_path = source_path
        if flow.request:
            self._active_panel = "request"
        elif flow.response:
            self._active_panel = "response"
        else:
            self._active_panel = "request"
        self._panel_order = ("request", "response")

    def compose(self) -> ComposeResult:
        request_renderable = self._build_request_detail(self._flow)
        response_renderable = self._build_response_detail(self._flow)
        yield Header(show_clock=False)
        yield Container(
            VerticalScroll(Static(request_renderable, id="request-detail"), id="request-container"),
            VerticalScroll(Static(response_renderable, id="response-detail"), id="response-container"),
            id="detail-container",
        )
        yield StatusBar()

    def on_mount(self) -> None:
        self._update_panel_visibility()
        self._update_status_bar()

    def action_go_back(self) -> None:
        """Return to the previous screen."""

        self.app.pop_screen()

    def action_cycle_detail_panel(self) -> None:
        """Toggle between request and response views when Tab is pressed."""

        next_panel = self._panel_order[1] if self._active_panel == self._panel_order[0] else self._panel_order[0]
        self._active_panel = next_panel
        self._update_panel_visibility()
        self._update_status_bar()

    @staticmethod
    def _build_request_detail(flow: HTTPFlow) -> Text:
        text = Text()
        request = flow.request
        if not request:
            text.append("No request data available for this flow.")
            return text

        lines = [
            f"Method: {request.method or '-'}",
            f"Host: {request.host or '-'}",
            f"Path: {request.path or '-'}",
            f"Scheme: {request.scheme or '-'}",
            f"HTTP Version: {request.http_version or '-'}",
        ]
        header_lines = _format_headers(request.headers.items(multi=True))
        if header_lines:
            lines.append("Headers:")
            lines.extend(f"  {line}" for line in header_lines)
        body_preview = _format_body_preview(request.get_text(strict=False))
        if body_preview:
            lines.append("Body:")
            body_lines = body_preview.splitlines() or [body_preview]
            lines.extend(f"  {line}" for line in body_lines)

        text.append("Request", style="bold")
        for line in lines:
            text.append("\n")
            text.append(line)
        return text

    @staticmethod
    def _build_response_detail(flow: HTTPFlow) -> Text:
        text = Text()
        response = flow.response
        if not response:
            text.append("No response data available for this flow.")
            return text

        lines = [
            f"Status: {response.status_code}",
            f"Reason: {response.reason or ''}",
            f"HTTP Version: {response.http_version or '-'}",
        ]
        header_lines = _format_headers(response.headers.items(multi=True))
        if header_lines:
            lines.append("Headers:")
            lines.extend(f"  {line}" for line in header_lines)
        body_preview = _format_body_preview(response.get_text(strict=False))
        if body_preview:
            lines.append("Body:")
            body_lines = body_preview.splitlines() or [body_preview]
            lines.extend(f"  {line}" for line in body_lines)

        text.append("Response", style="bold")
        for line in lines:
            text.append("\n")
            text.append(line)
        return text

    def _update_panel_visibility(self) -> None:
        request_container = self.query_one("#request-container", VerticalScroll)
        response_container = self.query_one("#response-container", VerticalScroll)
        request_container.styles.display = "block" if self._active_panel == "request" else "none"
        response_container.styles.display = "block" if self._active_panel == "response" else "none"
        active_container = request_container if self._active_panel == "request" else response_container
        self.set_focus(active_container)

    def _update_status_bar(self) -> None:
        status = self.query_one(StatusBar)
        view_label = "Request" if self._active_panel == "request" else "Response"
        status.update(
            f"Flow {self._position + 1}/{self._total} | Esc/Backspace back, q quit"
        )


def _format_headers(headers: Iterable[tuple[str, str]] | None) -> list[str]:
    """Format a headers mapping into display-ready lines."""

    if headers is None:
        return []

    return [f"{name}: {value}" for name, value in headers]


def _format_body_preview(text: str | None, limit: int = 2000) -> str:
    """Prepare a safe, trimmed text representation for body content."""

    if not text:
        return ""

    stripped = text.strip()
    if len(stripped) > limit:
        return stripped[: limit - 3] + "..."
    return stripped
