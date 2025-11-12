import type { Prediction } from "@/types/prediction";
import { getPredictionGrade, normalizeSummaryWithGrade } from "@/lib/prediction";

const percent = (value: number) => Math.round(value * 100);

export function PredictionCard({ prediction }: { prediction: Prediction }) {
  const homePercent = percent(prediction.homeWinProb);
  const awayPercent = percent(prediction.awayWinProb);
  const edgePercent = Math.round(Math.abs(prediction.edge) * 100);
  const favoriteTeam = prediction.modelFavorite === "home" ? prediction.homeTeam : prediction.awayTeam;
  const grade = getPredictionGrade(prediction.edge);
  const summary = normalizeSummaryWithGrade(prediction.summary, grade.label);

  return (
    <article className="group rounded-3xl border border-white/10 bg-white/5 p-6 text-white shadow-2xl shadow-black/20 backdrop-blur transition hover:-translate-y-1 hover:shadow-black/40">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-white/60">
            {prediction.startTimeEt ?? "TBD"}
          </p>
          <h3 className="mt-1 text-2xl font-semibold">
            {prediction.awayTeam.name} ({prediction.awayTeam.abbrev}) @ {prediction.homeTeam.name} ({prediction.homeTeam.abbrev})
          </h3>
          <p className="mt-2 text-sm text-white/80">
            Confidence {grade.label} · {favoriteTeam.name} lean
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase text-white/60">Model Edge</p>
          <p className="text-2xl font-semibold text-lime-300">
            {prediction.modelFavorite === "home" ? "Home" : "Road"} +{edgePercent}%
          </p>
          <p className="text-xs uppercase tracking-[0.4em] text-white/40">{grade.label} grade</p>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <ProbabilityBar label={`${prediction.homeTeam.name} (${prediction.homeTeam.abbrev})`} value={homePercent} highlight={prediction.modelFavorite === "home"} />
        <ProbabilityBar label={`${prediction.awayTeam.name} (${prediction.awayTeam.abbrev})`} value={awayPercent} highlight={prediction.modelFavorite === "away"} />
      </div>

      <dl className="mt-6 space-y-3 text-sm text-white/80">
        <div>
          <dt className="text-white/60">Venue</dt>
          <dd className="mt-1 text-base font-medium">{prediction.venue ?? "TBD"}</dd>
        </div>
        <div>
          <dt className="text-white/60">Why it matters</dt>
          <dd className="mt-1 text-base leading-relaxed text-white/90">{summary}</dd>
          <p className="mt-2 text-xs uppercase tracking-[0.4em] text-white/40">{grade.description}</p>
        </div>
      </dl>
    </article>
  );
}

function ProbabilityBar({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className={highlight ? "font-semibold text-white" : "text-white/70"}>{label}</span>
        <span className={highlight ? "text-lime-300" : "text-white/70"}>{value}%</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${highlight ? "bg-gradient-to-r from-lime-300 to-emerald-400" : "bg-white/30"}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
