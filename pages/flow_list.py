"""List page that shows all loaded HTTP flows."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mitmproxy.http import HTTPFlow
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Input

from widgets.status_bar import StatusBar
from pages.flow_detail import FlowDetailScreen


class FlowListScreen(Screen):
    """Screen displaying all captured HTTP flows in a table."""

    CSS = """
    FlowListScreen {
        layout: vertical;
    }

    #flow-table {
        height: 1fr;
        padding: 1;
    }

    #command-input {
        dock: bottom;
        height: 3;
        padding: 0 1;
        display: none;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("d", "half_page_down", "Half Down"),
        ("u", "half_page_up", "Half Up"),
        ("g", "jump_top", "Top"),
        ("G", "jump_bottom", "Bottom"),
        ("H", "jump_screen_top", "Screen Top"),
        ("L", "jump_screen_bottom", "Screen Bottom"),
        (":", "open_command", "Command Mode"),
        ("escape", "cancel_command", "Cancel Command"),
    ]

    def __init__(
        self,
        flows: Sequence[HTTPFlow],
        source_path: Path,
        content_type_filter: str | None = None,
    ) -> None:
        super().__init__()
        self._flows = list(flows)
        self._source_path = source_path
        self._content_type_filter = content_type_filter
        self._status_message: str | None = None
        self._command_input: Input | None = None
        self._command_active = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield DataTable(id="flow-table")
        yield StatusBar()
        command_input = Input(id="command-input", placeholder=": command")
        command_input.styles.display = "none"
        yield command_input

    def on_mount(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        table.add_columns("#", "Method", "Host", "Path", "Status")
        self._populate_table()
        table.cursor_type = "row"
        table.zebra_stripes = True

        self._command_input = self.query_one("#command-input", Input)
        self._command_input.styles.display = "none"

        self._update_status_bar()

    def action_move_down(self) -> None:
        self._move_cursor(1)

    def action_move_up(self) -> None:
        self._move_cursor(-1)

    def action_half_page_down(self) -> None:
        self._page_move(0.5)

    def action_half_page_up(self) -> None:
        self._page_move(-0.5)

    def action_jump_top(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        if table.row_count:
            table.cursor_coordinate = (0, table.cursor_coordinate.column)

    def action_jump_bottom(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        if table.row_count:
            last_row = table.row_count - 1
            table.cursor_coordinate = (last_row, table.cursor_coordinate.column)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open a detail screen when the user presses Enter on a row."""

        key_value = getattr(event.row_key, "value", event.row_key)
        try:
            index = int(key_value)
        except (TypeError, ValueError):
            return

        flow = self._flows[index]
        self.app.push_screen(
            FlowDetailScreen(
                flow=flow,
                position=index,
                total=len(self._flows),
                source_path=self._source_path,
            )
        )

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

    def action_jump_screen_top(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        if not table.row_count:
            return
        top_row, _ = self._visible_bounds(table)
        table.cursor_coordinate = (top_row, table.cursor_coordinate.column)
        self._scroll_table_to_row(table, top_row, align="start")

    def action_jump_screen_bottom(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        if not table.row_count:
            return
        top_row, bottom_row = self._visible_bounds(table)
        table.cursor_coordinate = (bottom_row, table.cursor_coordinate.column)
        self._scroll_table_to_row(table, bottom_row, align="end")

    def action_open_command(self) -> None:
        if self._command_prompt_visible():
            return
        self._show_command_prompt(":")

    def action_cancel_command(self) -> None:
        if self._command_prompt_visible():
            self._hide_command_prompt()

    def _move_cursor(self, offset: int) -> None:
        table = self.query_one("#flow-table", DataTable)
        if not table.row_count:
            return
        row = table.cursor_coordinate.row + offset
        row = max(0, min(row, table.row_count - 1))
        table.cursor_coordinate = (row, table.cursor_coordinate.column)

    def _page_move(self, fraction: float) -> None:
        table = self.query_one("#flow-table", DataTable)
        if not table.row_count:
            return
        visible_rows = min(table.row_count, self._estimate_visible_rows())
        rows = max(1, int(visible_rows * abs(fraction)))
        direction = 1 if fraction > 0 else -1
        self._move_cursor(rows * direction)

    def _visible_bounds(self, table: DataTable) -> tuple[int, int]:
        offset = getattr(table, "scroll_offset", None)
        top = int(getattr(offset, "y", 0) if offset is not None else 0)
        top = max(0, min(top, table.row_count - 1)) if table.row_count else 0
        visible = min(table.row_count, self._estimate_visible_rows())
        bottom = min(table.row_count - 1, top + max(0, visible - 1)) if table.row_count else 0
        return top, bottom

    def _estimate_visible_rows(self) -> int:
        height = getattr(self.size, "height", 0)
        usable = max(1, height - 4)
        return usable

    def _scroll_table_to_row(self, table: DataTable, row: int, align: str) -> None:
        scroll_to_row = getattr(table, "scroll_to_row", None)
        if callable(scroll_to_row):
            for kwargs in (
                {"row": row, "animate": False, "align": align},
                {"row": row, "animate": False},
                {"row": row},
            ):
                try:
                    scroll_to_row(**kwargs)  # type: ignore[arg-type]
                    return
                except TypeError:
                    continue

    def update_flows(
        self,
        flows: Sequence[HTTPFlow],
        content_type_filter: str | None,
        *,
        status_message: str | None = None,
    ) -> None:
        self._flows = list(flows)
        self._content_type_filter = content_type_filter
        if status_message is not None:
            self._status_message = status_message or None
        self._populate_table()
        self._update_status_bar()

    def _populate_table(self) -> None:
        table = self.query_one("#flow-table", DataTable)
        if table.row_count:
            previous_row = table.cursor_coordinate.row
            previous_column = table.cursor_coordinate.column
        else:
            previous_row = 0
            previous_column = 0
        table.clear()
        if not table.columns:
            table.add_columns("#", "Method", "Host", "Path", "Status")
        for index, flow in enumerate(self._flows, start=1):
            request = flow.request
            response = flow.response
            table.add_row(
                str(index),
                request.method if request else "-",
                request.host if request else "-",
                request.path if request else "-",
                str(response.status_code) if response else "-",
                key=str(index - 1),
            )
        if table.row_count:
            column_limit = len(table.columns) - 1 if table.columns else 0
            new_row = min(previous_row, table.row_count - 1)
            new_column = min(previous_column, max(0, column_limit))
            table.cursor_coordinate = (new_row, new_column)

    def _update_status_bar(self) -> None:
        status = self.query_one(StatusBar)
        status_text = (
            "Loaded "
            f"{len(self._flows)} flows from {self._source_path.name}"
            " | j/k move, q quit, Enter details"
        )
        if self._content_type_filter:
            status_text += f" | Filter: {self._content_type_filter}"
            if not self._flows:
                status_text += " (no matches)"
        if self._status_message:
            status_text += f" | {self._status_message}"
        status.update(status_text)

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
        table = self.query_one("#flow-table", DataTable)
        self.set_focus(table)

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

        if name == "set":
            self._handle_set_command(remainder, raw_command)
            return

        if name == "cp":
            self._handle_copy_command(remainder, raw_command)
            return

        self._set_status_message(f"Unknown command: {raw_command.strip()}")
        self.app.bell()

    def _set_status_message(self, message: str) -> None:
        self._status_message = message or None
        self._update_status_bar()

    def _copy_flow_section(self, section: str) -> None:
        flow = self._get_selected_flow()
        if flow is None:
            self._set_status_message("No flow selected to copy")
            self.app.bell()
            return

        if section == "request":
            request = flow.request
            if request is None:
                self._set_status_message("Selected flow has no request to copy")
                self.app.bell()
                return
            body = self._get_body_text(request.get_text(strict=False), request.raw_content)
            label = "Request body"
        else:
            response = flow.response
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

    def _get_selected_flow(self) -> HTTPFlow | None:
        table = self.query_one("#flow-table", DataTable)
        if not table.row_count:
            return None
        row_index = table.cursor_coordinate.row
        if 0 <= row_index < len(self._flows):
            return self._flows[row_index]
        return None

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

    def _handle_set_command(self, remainder: str, _: str) -> None:
        remainder = remainder.strip()
        if not remainder:
            self._set_status_message("Usage: :set ctype <value>")
            self.app.bell()
            return

        option_parts = remainder.split(None, 1)
        option = option_parts[0]
        value = option_parts[1] if len(option_parts) > 1 else ""

        if option != "ctype":
            self._set_status_message(f"Unknown option: {option}")
            self.app.bell()
            return

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1].strip()
        if not value:
            self.app.set_content_type_filter(
                None,
                status_message="Content-Type filter cleared",
            )
        else:
            self.app.set_content_type_filter(
                value,
                status_message=f"Content-Type filter set to {value}",
            )

    def _handle_copy_command(self, remainder: str, _: str) -> None:
        target = remainder.strip().lower()
        if not target:
            self._set_status_message("Usage: :cp request|response")
            self.app.bell()
            return

        aliases = {
            "req": "request",
            "request": "request",
            "resp": "response",
            "response": "response",
        }

        resolved = aliases.get(target)
        if not resolved:
            self._set_status_message(f"Unknown copy target: {target}")
            self.app.bell()
            return

        self._copy_flow_section(resolved)
