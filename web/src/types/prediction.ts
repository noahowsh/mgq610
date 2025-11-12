export type TeamInfo = {
  name: string;
  abbrev: string;
};

export type ConfidenceGrade = "A+" | "A" | "A-" | "B+" | "B" | "B-" | "C+" | "C";

export type Prediction = {
  id: string;
  gameDate: string;
  startTimeEt: string | null;
  startTimeUtc: string | null;
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  homeWinProb: number;
  awayWinProb: number;
  confidenceScore: number;
  confidenceGrade: ConfidenceGrade;
  edge: number;
  modelFavorite: "home" | "away";
  summary: string;
  venue?: string | null;
  season?: string | null;
};

export type PredictionsPayload = {
  generatedAt: string;
  games: Prediction[];
};
