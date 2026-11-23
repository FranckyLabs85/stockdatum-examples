"""x402 client for StockDatum Filings.

Free route: GET /sample/{dataset}
Paid route: GET /v1/form4 (published price 0.02 USDC). The recipient is the
payTo value on the server's HTTP 402 response. This module does not set one.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

API_ORIGIN = "https://api.stockdatum.com"
SAMPLE_DATASETS = ("8k", "form4", "form144", "clusters")
# Published on GET /pricing and OpenAPI x-price-usdc for GET /v1/form4.
FORM4_PRICE_USDC = "0.02"
# Above the published form4 price. A 402 above this cap is not signed.
SPEND_CAP_USD = "$0.05"
BASE_NETWORK = "eip155:8453"

_HEADERS = {"Accept": "application/json", "User-Agent": "stockdatum-examples"}
_TICKER = re.compile(r"^[A-Za-z0-9.\-]{1,10}$")
_CIK = re.compile(r"^\d{1,10}$")
_CODE = re.compile(r"^[A-Za-z]$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEX_KEY = re.compile(r"^[0-9a-fA-F]{64}$")


class ClientError(RuntimeError):
    """The StockDatum call failed before a usable JSON body was returned."""


def sample_url(dataset: str) -> str:
    if dataset not in SAMPLE_DATASETS:
        allowed = ", ".join(SAMPLE_DATASETS)
        raise ClientError(f"dataset must be one of: {allowed}")
    return f"{API_ORIGIN}/sample/{dataset}"


def build_form4_params(
    *,
    ticker: str | None = "AAPL",
    cik: str | None = None,
    since: str | None = None,
    code: str | None = None,
    limit: int = 1,
) -> dict[str, str]:
    """Build the small default form4 query, or a caller-supplied one.

    The API requires ticker or cik. limit is 1-200. The example default is
    ticker=AAPL and limit=1.
    """
    params: dict[str, str] = {}
    if ticker:
        if _TICKER.fullmatch(ticker) is None:
            raise ClientError("ticker must match ^[A-Za-z0-9.\\-]{1,10}$")
        params["ticker"] = ticker
    if cik:
        if _CIK.fullmatch(cik) is None:
            raise ClientError("cik must be 1-10 digits")
        params["cik"] = cik
    if "ticker" not in params and "cik" not in params:
        raise ClientError("GET /v1/form4 requires ticker or cik")
    if since:
        if _DATE.fullmatch(since) is None:
            raise ClientError("since must be YYYY-MM-DD")
        params["since"] = since
    if code:
        if _CODE.fullmatch(code) is None:
            raise ClientError("code must be one letter")
        params["code"] = code
    if limit < 1 or limit > 200:
        raise ClientError("limit must be an integer from 1 to 200")
    params["limit"] = str(limit)
    return params


def form4_url(params: dict[str, str]) -> str:
    return str(httpx.URL(f"{API_ORIGIN}/v1/form4", params=params))


def fetch_sample(dataset: str = "form4", *, timeout: float = 30.0) -> dict[str, Any]:
    """GET /sample/{dataset}. This route is free and does not read a key."""
    response = httpx.get(sample_url(dataset), headers=_HEADERS, timeout=timeout)
    return _json_object(response, f"GET /sample/{dataset}")


async def fetch_form4(
    params: dict[str, str],
    *,
    timeout: float = 60.0,
) -> tuple[dict[str, Any], bool]:
    """GET /v1/form4, paying the server's 402 challenge when rows are returned.

    Returns the JSON body and whether a PAYMENT-RESPONSE header was present.
    The header value is not returned: it can identify the paying wallet.
    """
    key = require_private_key()
    try:
        client = x402Client().set_spend_controls({"max_amount_per_payment": SPEND_CAP_USD})
        register_exact_evm_client(
            client,
            EthAccountSigner(Account.from_key(key)),
            networks=BASE_NETWORK,
        )
        async with x402HttpxClient(client, timeout=timeout) as http:
            response = await http.get(form4_url(params), headers=_HEADERS)
            await response.aread()
    except ClientError:
        raise
    except Exception as exc:
        _reraise_without_key(exc, key)

    settled = response.headers.get("PAYMENT-RESPONSE") is not None
    body = _json_object(response, "GET /v1/form4", settled=settled)
    return body, settled


def require_private_key() -> str:
    """Read EVM_PRIVATE_KEY. Refuse when CI=true unless STOCKDATUM_ALLOW_PAID=1."""
    if os.environ.get("CI") == "true" and os.environ.get("STOCKDATUM_ALLOW_PAID") != "1":
        raise ClientError("Refusing paid call because CI=true. Paid calls spend real USDC.")
    raw = os.environ.get("EVM_PRIVATE_KEY", "").strip()
    if not raw:
        raise ClientError(
            "EVM_PRIVATE_KEY is not set. Copy .env.example to .env. Paid calls spend real USDC."
        )
    body = raw[2:] if raw[:2].lower() == "0x" else raw
    if _HEX_KEY.fullmatch(body) is None:
        raise ClientError("EVM_PRIVATE_KEY must be 32 bytes of hex.")
    return "0x" + body


def _json_object(
    response: httpx.Response,
    label: str,
    *,
    settled: bool | None = None,
) -> dict[str, Any]:
    suffix = "" if settled is None else f" payment_settled={settled}"
    if response.status_code != 200:
        detail = response.text[:500]
        raise ClientError(f"{label} HTTP {response.status_code}{suffix} {detail}".rstrip())
    payload: object = response.json()
    if not isinstance(payload, dict):
        raise ClientError(f"{label} did not return a JSON object")
    return {str(key): value for key, value in payload.items()}


def _reraise_without_key(exc: Exception, key: str) -> None:
    text = str(exc)
    secret = key[2:]
    if key in text or secret in text:
        raise ClientError(
            "Paid call failed. Error text withheld because it contained the private key."
        ) from None
    raise exc
