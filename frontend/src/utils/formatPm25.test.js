import { describe, expect, it } from "vitest";
import { formatPm25, formatPm25WithUnit } from "./formatPm25.js";

describe("PM2.5 display formatting", () => {
  it("rounds finite values to one decimal without changing the input", () => {
    const value = 61.537499999999994;

    expect(formatPm25(value)).toBe("61.5");
    expect(formatPm25(20)).toBe("20.0");
    expect(formatPm25WithUnit(value, "µg/m³")).toBe("61.5 µg/m³");
    expect(value).toBe(61.537499999999994);
  });

  it.each([null, undefined, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    "uses the fallback for invalid value %s",
    (value) => {
      expect(formatPm25(value, "No reading")).toBe("No reading");
      expect(formatPm25WithUnit(value, "µg/m³", "No reading")).toBe("No reading");
    },
  );
});
