"""LangChain tools for StockDatum Filings sample and form4 calls.

stockdatum_sample calls GET /sample/{dataset} and does not spend USDC.
stockdatum_form4 calls GET /v1/form4. A response with rows costs 0.02 USDC.
The x402 client pays the payTo address on the server's 402 response.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from eth_account import Account
from langchain_core.tools import tool
from x402 import x402ClientSync
from x402.http.clients import x402_requests
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

API_ORIGIN = "https://api.stockdatum.com"
SAMPLE_DATASETS = ("8k", "form4", "form144", "clusters")
FORM4_PRICE_USDC = "0.02"
SPEND_CAP_USD = "$0.05"
BASE_NETWORK = "eip155:8453"
_HEADERS = {"Accept": "application/json", "User-Agent": "stockdatum-examples"}


class ClientError(RuntimeError):
    """The StockDatum call failed before a usable JSON body was returned."""


def load_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@tool
def stockdatum_sample(dataset: str = "form4") -> str:
    """Fetch a free StockDatum sample.

    dataset is one of 8k, form4, form144, clusters.
    Calls GET /sample/{dataset}. Does not spend USDC and does not read a key.
    """
    load_env()
    if dataset not in SAMPLE_DATASETS:
        allowed = ", ".join(SAMPLE_DATASETS)
        raise ClientError(f"dataset must be one of: {allowed}")
    response = httpx.get(
        f"{API_ORIGIN}/sample/{dataset}",
        headers=_HEADERS,
        timeout=30.0,
    )
    return json.dumps(_json_object(response, f"GET /sample/{dataset}"), indent=2)


@tool
def stockdatum_form4(
    ticker: str = "AAPL",
    limit: int = 1,
    cik: str = "",
    since: str = "",
    code: str = "",
) -> str:
    """Fetch Form 4 insider transaction lines from StockDatum.

    Calls GET /v1/form4. A response with rows costs 0.02 USDC via x402
    (scheme exact, USDC, Base eip155:8453). A valid response with zero rows
    is not charged. Requires EVM_PRIVATE_KEY. ticker or cik is required.
    Default query is ticker=AAPL and limit=1.
    """
    load_env()
    params = _form4_params(ticker=ticker, limit=limit, cik=cik, since=since, code=code)
    key = _require_private_key()
    client = x402ClientSync().set_spend_controls({"max_amount_per_payment": SPEND_CAP_USD})
    register_exact_evm_client(
        client,
        EthAccountSigner(Account.from_key(key)),
        networks=BASE_NETWORK,
    )
    url = str(httpx.URL(f"{API_ORIGIN}/v1/form4", params=params))
    try:
        with x402_requests(client) as session:
            response = session.get(url, headers=_HEADERS, timeout=60)
    except ClientError:
        raise
    except Exception as exc:
        text = str(exc)
        if key in text or key[2:] in text:
            raise ClientError(
                "Paid call failed. Error text withheld because it contained the private key."
            ) from None
        raise
    settled = response.headers.get("PAYMENT-RESPONSE") is not None
    # requests.Response.json is untyped here; parse the text ourselves.
    if response.status_code != 200:
        raise ClientError(
            f"GET /v1/form4 HTTP {response.status_code} payment_settled={settled} "
            f"{response.text[:500]}".rstrip()
        )
    payload: object = json.loads(response.text)
    if not isinstance(payload, dict):
        raise ClientError("GET /v1/form4 did not return a JSON object")
    body = {str(item_key): value for item_key, value in payload.items()}
    return json.dumps({"payment_settled": settled, "body": body}, indent=2)


def _form4_params(
    *,
    ticker: str,
    limit: int,
    cik: str,
    since: str,
    code: str,
) -> dict[str, str]:
    params: dict[str, str] = {}
    if ticker:
        if re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", ticker) is None:
            raise ClientError("ticker must match ^[A-Za-z0-9.\\-]{1,10}$")
        params["ticker"] = ticker
    if cik:
        if re.fullmatch(r"\d{1,10}", cik) is None:
            raise ClientError("cik must be 1-10 digits")
        params["cik"] = cik
    if "ticker" not in params and "cik" not in params:
        raise ClientError("GET /v1/form4 requires ticker or cik")
    if since:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", since) is None:
            raise ClientError("since must be YYYY-MM-DD")
        params["since"] = since
    if code:
        if re.fullmatch(r"[A-Za-z]", code) is None:
            raise ClientError("code must be one letter")
        params["code"] = code
    if limit < 1 or limit > 200:
        raise ClientError("limit must be an integer from 1 to 200")
    params["limit"] = str(limit)
    return params


def _require_private_key() -> str:
    if os.environ.get("CI") == "true" and os.environ.get("STOCKDATUM_ALLOW_PAID") != "1":
        raise ClientError("Refusing paid call because CI=true. Paid calls spend real USDC.")
    raw = os.environ.get("EVM_PRIVATE_KEY", "").strip()
    if not raw:
        raise ClientError(
            "EVM_PRIVATE_KEY is not set. Copy .env.example to .env. Paid calls spend real USDC."
        )
    body = raw[2:] if raw[:2].lower() == "0x" else raw
    if len(body) != 64 or any(char not in "0123456789abcdefABCDEF" for char in body):
        raise ClientError("EVM_PRIVATE_KEY must be 32 bytes of hex.")
    return "0x" + body


def _json_object(response: httpx.Response, label: str) -> dict[str, Any]:
    if response.status_code != 200:
        raise ClientError(f"{label} HTTP {response.status_code} {response.text[:500]}".rstrip())
    payload: object = response.json()
    if not isinstance(payload, dict):
        raise ClientError(f"{label} did not return a JSON object")
    return {str(key): value for key, value in payload.items()}
