"""Entry point script for the mitmproxy flow viewer."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable

from app import FlowViewerApp
from flows import load_flows


def main(args: Iterable[str]) -> None:
    parser = ArgumentParser(description="View mitmproxy HTTP flows in a Textual UI.")
    parser.add_argument("flows_file", help="Path to a mitmproxy .flows or .dump file to load.")
    parser.add_argument(
        "--content-type",
        dest="content_type",
        metavar="TYPE",
        help="Only include requests whose Content-Type header contains the given value.",
    )
    options = parser.parse_args(list(args))

    flows_path = Path(options.flows_file).expanduser().resolve()
    flows = load_flows(flows_path)

    app = FlowViewerApp(
        flows=flows,
        source_path=flows_path,
        content_type_filter=options.content_type,
    )
    app.run()


if __name__ == "__main__":
    main(sys.argv[1:])
