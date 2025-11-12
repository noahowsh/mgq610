export type GradeDetail = {
  label: string;
  description: string;
};

const tierLabelPattern = /([ABC][+-]?)(?:-|\s*)tier/gi;

export function getPredictionGrade(edge: number): GradeDetail {
  const pts = Math.abs(edge) * 100;
  if (pts >= 20) return { label: "A+", description: "Very high confidence (≥20 pts edge)" };
  if (pts >= 17) return { label: "A", description: "High confidence (17-19 pts edge)" };
  if (pts >= 14) return { label: "A-", description: "Solid confidence (14-16 pts edge)" };
  if (pts >= 10) return { label: "B+", description: "Above-average confidence (10-13 pts edge)" };
  if (pts >= 7) return { label: "B", description: "Moderate confidence (7-9 pts edge)" };
  if (pts >= 4) return { label: "B-", description: "Slight edge (4-6 pts)" };
  if (pts >= 2) return { label: "C+", description: "Marginal edge (2-3 pts)" };
  return { label: "C", description: "Near coin flip (<2 pts)" };
}

export function normalizeSummaryWithGrade(summary: string, gradeLabel: string): string {
  if (!summary) return summary;
  return summary.replace(tierLabelPattern, `${gradeLabel} tier`);
}
