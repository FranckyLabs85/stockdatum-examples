# stockdatum-examples

Example clients for the [StockDatum Filings API](https://api.stockdatum.com).

`GET /sample/{dataset}` is free. `dataset` is `8k`, `form4`, `form144`, or `clusters`. The paid routes are `GET /v1/8k`, `GET /v1/form4`, `GET /v1/form144`, and `GET /v1/clusters`. Payment is [x402](https://x402.org) v2, scheme `exact`, USDC on Base (`eip155:8453`). There is no account and no API key. Paths, parameters, and prices are in [openapi.json](https://api.stockdatum.com/openapi.json) and [GET /pricing](https://api.stockdatum.com/pricing).

Prices read from `GET /pricing` on 2026-11-23: `/v1/8k`, `/v1/form4`, and `/v1/form144` are 0.02 USDC; `/v1/clusters` is 0.03 USDC. Each price is flat for up to 200 rows. A valid paid request that returns zero rows is not charged. An unpaid call is HTTP 402 before parameters are checked. A verified payment with a bad parameter is HTTP 400 and is not charged. Read `/pricing` before paying; this file is not the price source.

**Paid calls spend real USDC** from the wallet in `EVM_PRIVATE_KEY`. The examples do not hardcode a recipient. The client pays the `payTo` address on the server's 402 response, and it will not sign a payment above $0.05. Making a paid request accepts the [terms](https://api.stockdatum.com/terms).

The API states that responses are not investment advice.

## Layout

- `python/` — x402 Python client (`x402[httpx,evm]`). `sample` calls `GET /sample/form4`. `form4` calls `GET /v1/form4?ticker=AAPL&limit=1`.
- `typescript/` — the same calls. The paid call is implemented twice, with `@x402/fetch` and `@x402/axios`.
- `langchain/` — LangChain tools `stockdatum_sample` and `stockdatum_form4`.
- `mcp/client.mcp.json` — streamable-HTTP client for the live MCP server `com.stockdatum/sec-filings` at `https://api.stockdatum.com/mcp`.

## Connect the MCP server

The endpoint is live. Registry name: `com.stockdatum/sec-filings`. Transport: streamable HTTP. `POST` a JSON-RPC message to `https://api.stockdatum.com/mcp`. `GET` is not the call.

`mcp/client.mcp.json`:

```json
{
  "mcpServers": {
    "stockdatum": {
      "type": "streamable-http",
      "url": "https://api.stockdatum.com/mcp"
    }
  }
}
```

`initialize` and `tools/list` are not charged. A paid `tools/call` uses the same parameters and USDC prices as the REST routes. Send the payment on `params._meta["x402/payment"]`. There is no API key.

## Quick start

Python 3.10+ and Node.js 20+.

### Free sample

```bash
cd python
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m stockdatum_example sample
```

```bash
cd typescript
npm install
npm run sample
```

```bash
cd langchain
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m stockdatum_langchain sample
```

`sample` takes an optional dataset: `8k`, `form4`, `form144`, or `clusters`. The default is `form4`.

### Paid form4 call

Copy the env template and set the key in `.env`. Do not commit `.env`.

```bash
cp python/.env.example python/.env
cp typescript/.env.example typescript/.env
cp langchain/.env.example langchain/.env
```

```bash
python -m stockdatum_example form4
npm run form4:fetch
npm run form4:axios
python -m stockdatum_langchain form4
```

Each of those sends `GET /v1/form4?ticker=AAPL&limit=1` and spends 0.02 USDC when rows are returned. `form4:fetch` and `form4:axios` are separate calls. Running both pays twice. Optional flags: `--ticker`, `--cik`, `--since`, `--code`, `--limit` (Python and TypeScript). The API requires `ticker` or `cik`. `limit` is an integer from 1 to 200.

Paid commands exit without signing when `CI=true`, unless `STOCKDATUM_ALLOW_PAID=1`.

## Environment variables

| Name | Used by | Purpose |
| --- | --- | --- |
| `EVM_PRIVATE_KEY` | paid calls | Hex private key, 32 bytes, `0x` prefix optional. Read from the environment only. |
| `CI` | paid calls | When `true` (as on GitHub Actions), paid commands refuse to run. |
| `STOCKDATUM_ALLOW_PAID` | paid calls | Set to `1` to allow a paid call when `CI=true`. |

## Checks

CI lints and typechecks the Python and TypeScript clients and runs the free sample calls. It does not make a paid call.

```bash
python -m venv .venv
.venv/bin/pip install -e "./python[dev]" -e "./langchain[dev]"
.venv/bin/ruff check python langchain
.venv/bin/ruff format --check python langchain
.venv/bin/pyright
cd typescript && npm ci && npm run lint && npm run typecheck && npm run sample
```

## License

MIT. Copyright (c) 2026 Franck Labs Ltd.
