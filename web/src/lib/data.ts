import predictionsRaw from "@/data/todaysPredictions.json";
import goaliePulseRaw from "@/data/goaliePulse.json";
import type { Prediction, PredictionsPayload } from "@/types/prediction";
import type { GoaliePulse } from "@/types/goalie";

export function getPredictionsPayload(): PredictionsPayload {
  return predictionsRaw as PredictionsPayload;
}

export function getGoaliePulse(): GoaliePulse {
  return goaliePulseRaw as GoaliePulse;
}

export function selectCurrentSlate(games: Prediction[]): Prediction[] {
  if (!games.length) {
    return [];
  }

  const dates = games
    .map((game) => game.gameDate)
    .filter((date): date is string => Boolean(date))
    .sort();

  const earliestDate = dates[0];
  if (!earliestDate) {
    return games;
  }

  return games.filter((game) => game.gameDate === earliestDate);
}
