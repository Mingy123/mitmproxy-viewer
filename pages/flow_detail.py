"""Detail page that shows information about a single HTTP flow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, TYPE_CHECKING, cast

from rich.text import Text
from mitmproxy.http import HTTPFlow
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static, Input

from widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from app import FlowViewerApp


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

    #command-input {
        dock: bottom;
        height: 3;
        padding: 0 1;
        display: none;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("backspace", "go_back", "Back"),
        ("q", "app.quit", "Quit"),
        ("tab", "cycle_detail_panel", "Switch Request/Response"),
        ("h", "show_request_panel", "Show Request"),
        ("l", "show_response_panel", "Show Response"),
        ("j", "next_flow", "Next Flow"),
        ("k", "previous_flow", "Previous Flow"),
        (":", "open_command", "Command Mode"),
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
        self._status_message: str | None = None
        self._command_input: Input | None = None
        self._command_active = False

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
        command_input = Input(id="command-input", placeholder=": command")
        command_input.styles.display = "none"
        yield command_input

    def on_mount(self) -> None:
        self._update_panel_visibility()
        self._update_status_bar()
        self._command_input = self.query_one("#command-input", Input)
        self._command_input.styles.display = "none"

    def action_go_back(self) -> None:
        """Return to the previous screen."""

        if self._command_prompt_visible():
            self._hide_command_prompt()
            return
        self.app.pop_screen()

    def action_cycle_detail_panel(self) -> None:
        """Toggle between request and response views when Tab is pressed."""

        next_panel = self._panel_order[1] if self._active_panel == self._panel_order[0] else self._panel_order[0]
        self._set_active_panel(next_panel)

    def action_show_request_panel(self) -> None:
        """Switch explicitly to the request view."""

        self._set_active_panel("request")

    def action_show_response_panel(self) -> None:
        """Switch explicitly to the response view."""

        self._set_active_panel("response")

    def action_next_flow(self) -> None:
        """Jump to the next flow when available."""

        self._navigate_flow(1)

    def action_previous_flow(self) -> None:
        """Jump to the previous flow when available."""

        self._navigate_flow(-1)

    def action_open_command(self) -> None:
        if self._command_prompt_visible():
            return
        self._show_command_prompt(":")

    def action_cancel_command(self) -> None:
        if self._command_prompt_visible():
            self._hide_command_prompt()

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
        status_text = (
            f"Flow {self._position + 1}/{self._total}"
            " | Esc/Bksp back, q quit"
        )
        if self._status_message:
            status_text += f" | {self._status_message}"
        status.update(status_text)

    def _navigate_flow(self, offset: int) -> None:
        app = cast("FlowViewerApp", self.app)
        flows = list(app.get_flows())
        if not flows:
            self.app.bell()
            return
        new_index = self._position + offset
        if new_index < 0 or new_index >= len(flows):
            self.app.bell()
            return
        self._flow = flows[new_index]
        self._position = new_index
        self._total = len(flows)
        self._set_status_message(None)
        app.focus_flow_in_list(new_index)
        self._refresh_detail_content()

    def _refresh_detail_content(self) -> None:
        request_renderable = self._build_request_detail(self._flow)
        response_renderable = self._build_response_detail(self._flow)
        request_static = self.query_one("#request-detail", Static)
        response_static = self.query_one("#response-detail", Static)
        request_static.update(request_renderable)
        response_static.update(response_renderable)
        self._update_panel_visibility()
        self._update_status_bar()

    def _set_active_panel(self, panel: str) -> None:
        if panel not in self._panel_order:
            return
        if self._active_panel == panel:
            return
        self._active_panel = panel
        self._update_panel_visibility()
        self._update_status_bar()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command-input":
            return
        event.stop()
        raw_value = event.value
        self._hide_command_prompt()
        self._handle_command(raw_value)

    def on_input_blurred(self, event: Input.Blurred) -> None:
        if event.input.id != "command-input":
            return
        if self._command_prompt_visible():
            self._hide_command_prompt()

    def _set_status_message(self, message: str) -> None:
        self._status_message = message or None
        self._update_status_bar()

    def _show_command_prompt(self, initial: str) -> None:
        if not self._command_input:
            return
        self._command_active = True
        self._command_input.styles.display = "block"
        self._command_input.value = initial
        self._command_input.cursor_position = len(self._command_input.value)
        self.set_focus(self._command_input)

    def _hide_command_prompt(self) -> None:
        if not self._command_input:
            return
        self._command_active = False
        self._command_input.value = ""
        self._command_input.styles.display = "none"
        active = (
            self.query_one("#request-container", VerticalScroll)
            if self._active_panel == "request"
            else self.query_one("#response-container", VerticalScroll)
        )
        self.set_focus(active)

    def _command_prompt_visible(self) -> bool:
        return self._command_active

    def _handle_command(self, raw_command: str) -> None:
        command = raw_command.strip()
        if not command:
            self._set_status_message("No command entered")
            return

        if command.startswith(":"):
            command = command[1:].lstrip()
        if not command:
            self._set_status_message("No command entered")
            return

        parts = command.split(None, 1)
        name = parts[0]
        remainder = parts[1] if len(parts) > 1 else ""

        if name == "cp":
            self._handle_copy_command(remainder, raw_command)
            return

        self._set_status_message(f"Unknown command: {raw_command.strip()}")
        self.app.bell()

    def _handle_copy_command(self, remainder: str, _: str) -> None:
        target = remainder.strip().lower()
        if not target:
            self._set_status_message("Usage: :cp request|response")
            self.app.bell()
            return

        aliases = {
            "req": "request",
            "request": "request",
            "res": "response",
            "resp": "response",
            "response": "response",
        }

        resolved = aliases.get(target)
        if not resolved:
            self._set_status_message(f"Unknown copy target: {target}")
            self.app.bell()
            return

        self._copy_flow_section(resolved)

    def _copy_flow_section(self, section: str) -> None:
        if section == "request":
            request = self._flow.request
            if request is None:
                self._set_status_message("Selected flow has no request to copy")
                self.app.bell()
                return
            body = self._get_body_text(request.get_text(strict=False), request.raw_content)
            label = "Request body"
        else:
            response = self._flow.response
            if response is None:
                self._set_status_message("Selected flow has no response to copy")
                self.app.bell()
                return
            body = self._get_body_text(response.get_text(strict=False), response.raw_content)
            label = "Response body"

        self.app.copy_to_clipboard(body)
        if body:
            self._set_status_message(f"{label} copied to clipboard")
        else:
            self._set_status_message(f"{label} copied to clipboard (empty)")

    @staticmethod
    def _get_body_text(text_value: str | None, raw_content: bytes | None) -> str:
        if text_value:
            return text_value
        if raw_content:
            try:
                return raw_content.decode("utf-8")
            except UnicodeDecodeError:
                return raw_content.decode("utf-8", errors="replace")
        return ""


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
