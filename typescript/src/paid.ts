import { x402Client } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { privateKeyToAccount } from "viem/accounts";

import { BASE_NETWORK, SPEND_CAP_USD, type Form4Query, form4Url } from "./api.js";

const HEX_KEY = /^[0-9a-fA-F]{64}$/;

/** Read EVM_PRIVATE_KEY. Refuse when CI=true unless STOCKDATUM_ALLOW_PAID=1. */
export function requirePrivateKey(): `0x${string}` {
  if (process.env.CI === "true" && process.env.STOCKDATUM_ALLOW_PAID !== "1") {
    throw new Error("Refusing paid call because CI=true. Paid calls spend real USDC.");
  }
  const raw = process.env.EVM_PRIVATE_KEY?.trim() ?? "";
  if (!raw) {
    throw new Error(
      "EVM_PRIVATE_KEY is not set. Copy .env.example to .env. Paid calls spend real USDC.",
    );
  }
  const body = raw.slice(0, 2).toLowerCase() === "0x" ? raw.slice(2) : raw;
  if (!HEX_KEY.test(body)) {
    throw new Error("EVM_PRIVATE_KEY must be 32 bytes of hex.");
  }
  return `0x${body}`;
}

/**
 * x402 client for Base. The server's 402 response supplies payTo.
 * This function does not log the key or the payer address.
 */
export function createPaymentClient(privateKey: `0x${string}`): x402Client {
  const signer = privateKeyToAccount(privateKey);
  return new x402Client()
    .register(BASE_NETWORK, new ExactEvmScheme(signer))
    .setSpendControls({ maxAmountPerPayment: SPEND_CAP_USD });
}

export function defaultForm4Url(): string {
  return form4Url({ ticker: "AAPL", limit: 1 });
}

export function form4UrlFromFlags(flags: Map<string, string>): string {
  const query: Form4Query = { limit: 1, ticker: "AAPL" };
  const ticker = flags.get("ticker");
  const cik = flags.get("cik");
  const since = flags.get("since");
  const code = flags.get("code");
  const limit = flags.get("limit");
  if (ticker !== undefined) {
    query.ticker = ticker;
  }
  if (cik) {
    query.cik = cik;
  }
  if (since) {
    query.since = since;
  }
  if (code) {
    query.code = code;
  }
  if (limit !== undefined) {
    query.limit = Number(limit);
  }
  return form4Url(query);
}

export function scrub(message: string, privateKey: string): string {
  const body = privateKey.slice(2);
  if (!message.includes(privateKey) && !message.includes(body)) {
    return message;
  }
  return "Paid call failed. Error text withheld because it contained the private key.";
}
