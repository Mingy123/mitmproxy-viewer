"""Helpers for loading mitmproxy flow captures."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mitmproxy import io
from mitmproxy.exceptions import FlowReadException
from mitmproxy.http import HTTPFlow


def load_flows(path: Path) -> Sequence[HTTPFlow]:
    """Load HTTP flows from a mitmproxy dump file."""

    if not path.exists():
        raise SystemExit(f"Flows file not found: {path}")
    if not path.is_file():
        raise SystemExit(f"Flows path is not a file: {path}")

    flows: list[HTTPFlow] = []
    with path.open("rb") as input_file:
        reader = io.FlowReader(input_file)
        try:
            for flow in reader.stream():
                flows.append(flow)
        except FlowReadException as error:
            raise SystemExit(f"Failed to read flows: {error}") from error
    return flows


def filter_flows_by_content_type(flows: Sequence[HTTPFlow], content_type: str) -> list[HTTPFlow]:
    """Return flows whose request Content-Type header contains the provided value."""

    if not content_type:
        return list(flows)

    needle = content_type.lower()
    filtered: list[HTTPFlow] = []
    for flow in flows:
        request = flow.request
        if not request:
            continue
        header_value = request.headers.get("content-type")
        if header_value and needle in header_value.lower():
            filtered.append(flow)
    return filtered
