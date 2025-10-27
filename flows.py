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
