"""Command line for the StockDatum example client.

    python -m stockdatum_example sample [8k|form4|form144|clusters]
    python -m stockdatum_example form4 [--ticker AAPL] [--limit 1]

`sample` is free. `form4` spends real USDC when the response contains rows.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from stockdatum_example.client import (
    SAMPLE_DATASETS,
    ClientError,
    build_form4_params,
    fetch_form4,
    fetch_sample,
)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    parser = argparse.ArgumentParser(description="StockDatum Filings example client")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample", help="GET /sample/{dataset} (free)")
    sample.add_argument("dataset", nargs="?", default="form4", choices=SAMPLE_DATASETS)

    form4 = sub.add_parser("form4", help="GET /v1/form4 (0.02 USDC when rows are returned)")
    form4.add_argument("--ticker", default="AAPL")
    form4.add_argument("--cik", default="")
    form4.add_argument("--since", default="")
    form4.add_argument("--code", default="")
    form4.add_argument("--limit", type=int, default=1)

    args = parser.parse_args(argv)
    try:
        if args.command == "sample":
            body = fetch_sample(args.dataset)
            _emit(body)
            return 0
        params = build_form4_params(
            ticker=args.ticker or None,
            cik=args.cik or None,
            since=args.since or None,
            code=args.code or None,
            limit=args.limit,
        )
        body, settled = asyncio.run(fetch_form4(params))
        print(f"payment_settled={settled}", file=sys.stderr)
        _emit(body)
    except ClientError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _emit(body: dict[str, Any]) -> None:
    json.dump(body, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
