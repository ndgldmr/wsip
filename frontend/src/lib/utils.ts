import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Converts YYYY-MM-DD to ISO week key integer YYYYWW. */
export function dateToWeekKey(dateStr: string): number {
  const d = new Date(dateStr + "T00:00:00");
  // Thursday of the same week (ISO week belongs to the year containing its Thursday)
  const thursday = new Date(d);
  thursday.setDate(d.getDate() - ((d.getDay() + 6) % 7) + 3);
  const yearStart = new Date(thursday.getFullYear(), 0, 4);
  const startThursday = new Date(yearStart);
  startThursday.setDate(yearStart.getDate() - ((yearStart.getDay() + 6) % 7) + 3);
  const week = Math.round((thursday.getTime() - startThursday.getTime()) / 604800000) + 1;
  return thursday.getFullYear() * 100 + week;
}

/** Returns fromWeek/toWeek for the N weeks ending on (and including) the week of asOf. */
export function weekRange(asOf: string, weeksBack: number): { fromWeek: number; toWeek: number } {
  const toWeek = dateToWeekKey(asOf);
  const d = new Date(asOf + "T00:00:00");
  d.setDate(d.getDate() - 7 * (weeksBack - 1));
  const fromWeek = dateToWeekKey(d.toISOString().slice(0, 10));
  return { fromWeek, toWeek };
}

/** Today's date as YYYY-MM-DD. */
export function today(): string {
  return new Date().toISOString().slice(0, 10);
}
