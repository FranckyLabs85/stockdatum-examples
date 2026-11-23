import axios from "axios";
import { config as loadEnv } from "dotenv";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { wrapAxiosWithPayment } from "@x402/axios";
import { wrapFetchWithPayment } from "@x402/fetch";

import { isSampleDataset } from "./api.js";
import { createPaymentClient, form4UrlFromFlags, requirePrivateKey, scrub } from "./paid.js";
import { fetchSample } from "./sample.js";

loadEnv({
  path: resolve(dirname(fileURLToPath(import.meta.url)), "../.env"),
  quiet: true,
});

const command = process.argv[2] ?? "sample";

try {
  if (command === "sample") {
    const dataset = process.argv[3] ?? "form4";
    if (!isSampleDataset(dataset)) {
      throw new Error("dataset must be one of: 8k, form4, form144, clusters");
    }
    const body = await fetchSample(dataset);
    console.log(JSON.stringify(body, null, 2));
  } else if (command === "form4-fetch") {
    await payWithFetch();
  } else if (command === "form4-axios") {
    await payWithAxios();
  } else {
    console.error("usage: tsx src/cli.ts [sample [dataset]|form4-fetch|form4-axios]");
    process.exitCode = 2;
  }
} catch (error) {
  const message = error instanceof Error ? error.message : "request failed";
  console.error(message);
  process.exitCode = 1;
}

function readFlags(): Map<string, string> {
  const flags = new Map<string, string>();
  const args = process.argv.slice(3);
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index];
    if (token === undefined || !token.startsWith("--")) {
      continue;
    }
    const value = args[index + 1];
    if (value === undefined || value.startsWith("--")) {
      throw new Error(`missing value for ${token}`);
    }
    flags.set(token.slice(2), value);
    index += 1;
  }
  return flags;
}

async function payWithFetch(): Promise<void> {
  const privateKey = requirePrivateKey();
  const url = form4UrlFromFlags(readFlags());
  try {
    const fetchWithPayment = wrapFetchWithPayment(fetch, createPaymentClient(privateKey));
    const response = await fetchWithPayment(url, {
      method: "GET",
      headers: { Accept: "application/json", "User-Agent": "stockdatum-examples" },
    });
    const settled = response.headers.get("PAYMENT-RESPONSE") !== null;
    const text = await response.text();
    if (!response.ok) {
      throw new Error(
        `GET /v1/form4 HTTP ${response.status} payment_settled=${settled} ${text.slice(0, 500)}`.trim(),
      );
    }
    console.error(`payment_settled=${settled}`);
    console.log(text);
  } catch (error) {
    const message = error instanceof Error ? error.message : "GET /v1/form4 failed";
    throw new Error(scrub(message, privateKey));
  }
}

async function payWithAxios(): Promise<void> {
  const privateKey = requirePrivateKey();
  const url = form4UrlFromFlags(readFlags());
  const api = wrapAxiosWithPayment(axios.create(), createPaymentClient(privateKey));
  try {
    const response = await api.get(url, {
      headers: { Accept: "application/json", "User-Agent": "stockdatum-examples" },
      timeout: 60_000,
    });
    const header = response.headers["payment-response"] ?? response.headers["PAYMENT-RESPONSE"];
    console.error(`payment_settled=${header !== undefined}`);
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const data = error.response?.data;
      const detail =
        data === undefined
          ? ""
          : typeof data === "string"
            ? data.slice(0, 500)
            : JSON.stringify(data).slice(0, 500);
      throw new Error(
        scrub(
          `GET /v1/form4 failed${status ? ` HTTP ${status}` : ""} ${detail}`.trim(),
          privateKey,
        ),
      );
    }
    const message = error instanceof Error ? error.message : "GET /v1/form4 failed";
    throw new Error(scrub(message, privateKey));
  }
}
