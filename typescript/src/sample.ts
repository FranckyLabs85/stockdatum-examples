import { HEADERS, sampleUrl } from "./api.js";

/** GET /sample/{dataset}. Free. Does not read a private key. */
export async function fetchSample(dataset: string): Promise<unknown> {
  const url = sampleUrl(dataset);
  const response = await fetch(url, { headers: HEADERS });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`GET /sample/${dataset} HTTP ${response.status} ${text.slice(0, 500)}`.trim());
  }
  return JSON.parse(text) as unknown;
}
