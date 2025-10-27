"""Detail page that shows information about a single HTTP flow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rich.text import Text
from mitmproxy.http import HTTPFlow
from textual.app import ComposeResult
from textual.containers import VerticalScroll
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
    }

    #flow-detail {
        padding: 1;
        border: solid $surface;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("backspace", "go_back", "Back"),
        ("q", "app.quit", "Quit"),
    ]

    def __init__(self, *, flow: HTTPFlow, position: int, total: int, source_path: Path) -> None:
        super().__init__()
        self._flow = flow
        self._position = position
        self._total = total
        self._source_path = source_path

    def compose(self) -> ComposeResult:
        detail_renderable = self._build_flow_details(self._flow)
        yield Header(show_clock=False)
        yield VerticalScroll(Static(detail_renderable, id="flow-detail"), id="detail-container")
        yield StatusBar()

    def on_mount(self) -> None:
        status = self.query_one(StatusBar)
        status.update(
            f"Flow {self._position + 1}/{self._total} from {self._source_path.name} | Esc/Backspace back, q quit"
        )

    def action_go_back(self) -> None:
        """Return to the previous screen."""

        self.app.pop_screen()

    @staticmethod
    def _build_flow_details(flow: HTTPFlow) -> Text:
        """Construct a Rich Text renderable describing the flow."""

        text = Text()
        has_content = False

        def append_section(title: str, lines: list[str]) -> None:
            nonlocal has_content
            if has_content:
                text.append("\n\n")
            has_content = True
            text.append(title, style="bold")
            if lines:
                text.append("\n")
                for index, line in enumerate(lines):
                    if index:
                        text.append("\n")
                    text.append(line)

        request = flow.request
        if request:
            request_lines = [
                f"Method: {request.method or '-'}",
                f"Host: {request.host or '-'}",
                f"Path: {request.path or '-'}",
                f"Scheme: {request.scheme or '-'}",
                f"HTTP Version: {request.http_version or '-'}",
            ]
            header_lines = _format_headers(request.headers.items(multi=True))
            if header_lines:
                request_lines.append("Headers:")
                request_lines.extend(f"  {line}" for line in header_lines)
            body_preview = _format_body_preview(request.get_text(strict=False))
            if body_preview:
                request_lines.append("Body:")
                body_lines = body_preview.splitlines() or [body_preview]
                request_lines.extend(f"  {line}" for line in body_lines)
            append_section("Request", request_lines)

        response = flow.response
        if response:
            response_lines = [
                f"Status: {response.status_code}",
                f"Reason: {response.reason or ''}",
                f"HTTP Version: {response.http_version or '-'}",
            ]
            header_lines = _format_headers(response.headers.items(multi=True))
            if header_lines:
                response_lines.append("Headers:")
                response_lines.extend(f"  {line}" for line in header_lines)
            body_preview = _format_body_preview(response.get_text(strict=False))
            if body_preview:
                response_lines.append("Body:")
                body_lines = body_preview.splitlines() or [body_preview]
                response_lines.extend(f"  {line}" for line in body_lines)
            append_section("Response", response_lines)

        if not has_content:
            text.append("No request or response data available for this flow.")

        return text


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
