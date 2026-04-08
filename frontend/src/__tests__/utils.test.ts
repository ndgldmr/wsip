import { describe, it, expect } from "vitest";
import { today, dateToWeekKey, weekRange } from "../lib/utils";

describe("today", () => {
  it("returns a YYYY-MM-DD formatted string", () => {
    const result = today();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("matches the current date", () => {
    const result = today();
    const expected = new Date().toISOString().slice(0, 10);
    expect(result).toBe(expected);
  });
});

describe("dateToWeekKey", () => {
  it("returns an integer in YYYYWW format", () => {
    const key = dateToWeekKey("2026-04-08");
    expect(typeof key).toBe("number");
    expect(key).toBeGreaterThan(202600);
    expect(key).toBeLessThan(202700);
  });

  it("returns consistent values for the same date", () => {
    expect(dateToWeekKey("2026-01-01")).toBe(dateToWeekKey("2026-01-01"));
  });
});

describe("weekRange", () => {
  it("returns fromWeek <= toWeek", () => {
    const { fromWeek, toWeek } = weekRange("2026-04-08", 4);
    expect(fromWeek).toBeLessThanOrEqual(toWeek);
  });

  it("returns exactly 1 week when weeksBack=1", () => {
    const { fromWeek, toWeek } = weekRange("2026-04-08", 1);
    expect(fromWeek).toBe(toWeek);
  });
});
