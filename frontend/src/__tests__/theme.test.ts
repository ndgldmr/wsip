import { describe, it, expect } from "vitest";
import { SCORE_COLOR, SEVERITY_COLOR } from "../lib/theme";

describe("SCORE_COLOR", () => {
  it("returns red for high scores (> 0.7)", () => {
    expect(SCORE_COLOR(0.8)).toBe("#ff3355");
    expect(SCORE_COLOR(1.0)).toBe("#ff3355");
    expect(SCORE_COLOR(0.71)).toBe("#ff3355");
  });

  it("returns amber for medium scores (> 0.4, ≤ 0.7)", () => {
    expect(SCORE_COLOR(0.5)).toBe("#ffab00");
    expect(SCORE_COLOR(0.7)).toBe("#ffab00");
    expect(SCORE_COLOR(0.41)).toBe("#ffab00");
  });

  it("returns green for low scores (≤ 0.4)", () => {
    expect(SCORE_COLOR(0.0)).toBe("#00e090");
    expect(SCORE_COLOR(0.4)).toBe("#00e090");
    expect(SCORE_COLOR(0.2)).toBe("#00e090");
  });
});

describe("SEVERITY_COLOR", () => {
  it("maps high to danger red", () => {
    expect(SEVERITY_COLOR.high).toBe("#ff3355");
  });

  it("maps medium to amber", () => {
    expect(SEVERITY_COLOR.medium).toBe("#ffab00");
  });

  it("maps low to green", () => {
    expect(SEVERITY_COLOR.low).toBe("#00e090");
  });
});
