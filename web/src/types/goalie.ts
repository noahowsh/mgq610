export type GoalieCard = {
  name: string;
  team: string;
  rollingGsa: number;
  seasonGsa: number;
  restDays: number;
  startLikelihood: number; // 0-1
  trend: "surging" | "steady" | "fresh" | "fatigue watch" | string;
  note: string;
  strengths: string[];
  watchouts: string[];
  nextOpponent: string;
};

export type GoaliePulse = {
  updatedAt: string;
  notes: string;
  goalies: GoalieCard[];
};
