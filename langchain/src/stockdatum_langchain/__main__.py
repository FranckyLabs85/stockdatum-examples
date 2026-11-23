"""Run one LangChain tool.

    python -m stockdatum_langchain sample [dataset]
    python -m stockdatum_langchain form4

`form4` spends real USDC when the response contains rows.
"""

from __future__ import annotations

import sys

from stockdatum_langchain.tools import ClientError, load_env, stockdatum_form4, stockdatum_sample


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "sample"
    try:
        if command == "sample":
            dataset = args[1] if len(args) > 1 else "form4"
            print(stockdatum_sample.invoke({"dataset": dataset}))
            return 0
        if command == "form4":
            print(stockdatum_form4.invoke({"ticker": "AAPL", "limit": 1}))
            return 0
    except ClientError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("usage: python -m stockdatum_langchain [sample [dataset]|form4]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
