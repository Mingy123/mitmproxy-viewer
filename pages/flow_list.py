"""List page that shows all loaded HTTP flows."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mitmproxy.http import HTTPFlow
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header

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
    ]

    def __init__(self, flows: Sequence[HTTPFlow], source_path: Path) -> None:
        super().__init__()
        self._flows = flows
        self._source_path = source_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield DataTable(id="flow-table")
        yield StatusBar()

    def on_mount(self) -> None:
        table = self.query_one("#flow-table", DataTable)
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
        table.cursor_type = "row"
        table.zebra_stripes = True

        status = self.query_one(StatusBar)
        status_text = (
            "Loaded "
            f"{len(self._flows)} flows from {self._source_path.name}"
            " | j/k move, q quit, Enter details"
        )
        status.update(status_text)

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
