import { describe, expect, it } from "vitest";

import { isHollowResult } from "./hollow-result.js";

describe("isHollowResult", () => {
  it("treats null/undefined as hollow", () => {
    expect(isHollowResult(null)).toBe(true);
    expect(isHollowResult(undefined)).toBe(true);
  });

  it("treats empty and whitespace strings as hollow", () => {
    expect(isHollowResult("")).toBe(true);
    expect(isHollowResult("   \n\t")).toBe(true);
  });

  it("treats non-empty strings as content", () => {
    expect(isHollowResult("874")).toBe(false);
  });

  it("treats numbers and booleans as content, including 0 and false", () => {
    expect(isHollowResult(0)).toBe(false);
    expect(isHollowResult(false)).toBe(false);
    expect(isHollowResult(1786)).toBe(false);
    expect(isHollowResult(true)).toBe(false);
  });

  it("treats empty arrays and arrays of hollow items as hollow", () => {
    expect(isHollowResult([])).toBe(true);
    expect(isHollowResult([""])).toBe(true);
    expect(isHollowResult([{}, { name: "  " }])).toBe(true);
  });

  it("treats arrays with any content as non-hollow", () => {
    expect(isHollowResult(["x"])).toBe(false);
    expect(isHollowResult([{ name: "" }, { name: "Drought" }])).toBe(false);
  });

  it("treats objects whose values are all hollow as hollow", () => {
    expect(isHollowResult({})).toBe(true);
    expect(isHollowResult({ a: "", b: null, c: [], d: { e: "" } })).toBe(true);
  });

  it("treats objects with any meaningful leaf as non-hollow", () => {
    expect(isHollowResult({ a: "", b: 874 })).toBe(false);
    expect(isHollowResult({ a: "", b: { c: "text" } })).toBe(false);
    expect(isHollowResult({ a: "", b: false })).toBe(false);
  });

  it("flags the 2026-10-02 incident payload (empty skeleton from the LBA request)", () => {
    const incident = {
      consensus_points: [],
      debate_characterization: "",
      evidence_quote: "",
      explanations: [],
      unresolved_questions: [],
    };
    expect(isHollowResult(incident)).toBe(true);
  });

  it("does not flag a substantive extraction result", () => {
    const substantive = {
      consensus_points: ["The collapse has no agreed single cause."],
      debate_characterization: "Multifactorial and unsettled.",
      evidence_quote: "According to Landnámabók...",
      explanations: [
        {
          name: "Drought",
          mechanism: "Severe dry period.",
          evidence_quote: "Juniper tree ring measurements...",
          weakness_or_counterargument: null,
        },
      ],
      unresolved_questions: ["What caused it?"],
    };
    expect(isHollowResult(substantive)).toBe(false);
  });

  it("does not flag a minimal but real answer (numbers only)", () => {
    expect(isHollowResult({ settlement_year: 874, municipal_charter_year: 1786 })).toBe(
      false,
    );
  });
});
