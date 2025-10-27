"""Entry point script for the mitmproxy flow viewer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from app import FlowViewerApp
from flows import load_flows


def main(args: Iterable[str]) -> None:
    argv = list(args)
    if len(argv) != 1:
        raise SystemExit("Usage: python main.py <flows-file>")

    flows_path = Path(argv[0]).expanduser().resolve()
    flows = load_flows(flows_path)

    app = FlowViewerApp(flows=flows, source_path=flows_path)
    app.run()


if __name__ == "__main__":
    main(sys.argv[1:])
