import { describe, expect, it } from "vitest";
import en from "./en.json";
import hi from "./hi.json";
import mr from "./mr.json";

function shape(value) {
  if (Array.isArray(value)) return value.map(shape);
  if (value === null || typeof value !== "object") return typeof value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    key,
    item && typeof item === "object" ? shape(item) : typeof item,
  ]));
}

describe("locale dictionaries", () => {
  it("have matching keys in English, Hindi, and Marathi", () => {
    expect(shape(hi)).toEqual(shape(en));
    expect(shape(mr)).toEqual(shape(en));
  });

  it("provide three concise poster advice lines for every status", () => {
    for (const locale of [en, hi, mr]) {
      for (const status of ["green", "yellow", "red", "unknown"]) {
        expect(locale.posterAdvice[status]).toHaveLength(3);
        expect(locale.posterAdvice[status].every((line) => line.length > 0)).toBe(true);
      }
    }
  });

  it("translate every smoke-hint state and safety note", () => {
    for (const locale of [en, hi, mr]) {
      for (const key of [
        "smokeTitle", "smokeLoading", "smokeUnconfigured", "smokeUnavailable",
        "smokeNoDetections", "smokeStale", "smokeRelevant", "smokeDisclaimer",
        "smokeWindUnavailable", "smokeWindIndeterminate", "smokeNoUpwindClusters",
        "smokeTransportPossible", "smokeClusterList", "smokeWindFrom",
      ]) {
        expect(locale[key].length).toBeGreaterThan(0);
      }
    }
  });
});
