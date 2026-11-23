/** StockDatum Filings paths taken from the OpenAPI document. No addresses. */

export const API_ORIGIN = "https://api.stockdatum.com";
export const SAMPLE_DATASETS = ["8k", "form4", "form144", "clusters"] as const;
export type SampleDataset = (typeof SAMPLE_DATASETS)[number];

/** Published price of GET /v1/form4, in USDC. Read GET /pricing for the current figure. */
export const FORM4_PRICE_USDC = "0.02";
/** Per-payment cap. A 402 above this is not signed. */
export const SPEND_CAP_USD = "$0.05";
/** Paid routes use this network (Base). */
export const BASE_NETWORK = "eip155:8453";

export const HEADERS = {
  Accept: "application/json",
  "User-Agent": "stockdatum-examples",
} as const;

const TICKER = /^[A-Za-z0-9.-]{1,10}$/;
const CIK = /^\d{1,10}$/;
const CODE = /^[A-Za-z]$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function sampleUrl(dataset: string): string {
  if (!isSampleDataset(dataset)) {
    throw new Error(`dataset must be one of: ${SAMPLE_DATASETS.join(", ")}`);
  }
  return `${API_ORIGIN}/sample/${dataset}`;
}

export function isSampleDataset(dataset: string): dataset is SampleDataset {
  return (SAMPLE_DATASETS as readonly string[]).includes(dataset);
}

export interface Form4Query {
  ticker?: string;
  cik?: string;
  since?: string;
  code?: string;
  limit: number;
}

export function buildForm4Params(query: Form4Query): URLSearchParams {
  const params = new URLSearchParams();
  if (query.ticker) {
    if (!TICKER.test(query.ticker)) {
      throw new Error("ticker must match ^[A-Za-z0-9.\\-]{1,10}$");
    }
    params.set("ticker", query.ticker);
  }
  if (query.cik) {
    if (!CIK.test(query.cik)) {
      throw new Error("cik must be 1-10 digits");
    }
    params.set("cik", query.cik);
  }
  if (!params.has("ticker") && !params.has("cik")) {
    throw new Error("GET /v1/form4 requires ticker or cik");
  }
  if (query.since) {
    if (!DATE.test(query.since)) {
      throw new Error("since must be YYYY-MM-DD");
    }
    params.set("since", query.since);
  }
  if (query.code) {
    if (!CODE.test(query.code)) {
      throw new Error("code must be one letter");
    }
    params.set("code", query.code);
  }
  if (!Number.isInteger(query.limit) || query.limit < 1 || query.limit > 200) {
    throw new Error("limit must be an integer from 1 to 200");
  }
  params.set("limit", String(query.limit));
  return params;
}

export function form4Url(query: Form4Query): string {
  return `${API_ORIGIN}/v1/form4?${buildForm4Params(query).toString()}`;
}
