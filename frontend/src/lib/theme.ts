export const SEVERITY_COLOR = {
  critical: "#ff3355",
  high:     "#ff3355",
  medium:   "#ffab00",
  low:      "#00e090",
} as const;

export type Severity = keyof typeof SEVERITY_COLOR;

/** Returns a hex color based on a 0–1 score (higher = worse). */
export const SCORE_COLOR = (score: number): string =>
  score > 0.7 ? "#ff3355" : score > 0.4 ? "#ffab00" : "#00e090";
