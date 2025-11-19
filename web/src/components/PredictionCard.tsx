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
  const dayOfInfo = prediction.dayOfInfo;
  const homeGoalie = dayOfInfo?.homeGoalie;
  const awayGoalie = dayOfInfo?.awayGoalie;
  const homeInjuryCount = dayOfInfo?.homeInjuryCount ?? 0;
  const awayInjuryCount = dayOfInfo?.awayInjuryCount ?? 0;
  const totalInjuries = homeInjuryCount + awayInjuryCount;

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
      {dayOfInfo && (
        <div className="mt-6 flex flex-wrap items-center gap-2">
          {homeGoalie && (
            <StatusChip
              label={`Home ${homeGoalie.goalieName ?? "goalie"} (${homeGoalie.confirmedStart ? "confirmed" : "projected"})`}
              detail={homeGoalie.statusDescription ?? undefined}
              tone={homeGoalie.confirmedStart ? "success" : homeGoalie.statusCode ? "warning" : "info"}
            />
          )}
          {awayGoalie && (
            <StatusChip
              label={`Away ${awayGoalie.goalieName ?? "goalie"} (${awayGoalie.confirmedStart ? "confirmed" : "projected"})`}
              detail={awayGoalie.statusDescription ?? undefined}
              tone={awayGoalie.confirmedStart ? "success" : awayGoalie.statusCode ? "warning" : "info"}
            />
          )}
          <StatusChip
            label={`Injuries ${homeInjuryCount}/${awayInjuryCount}`}
            tone={totalInjuries > 0 ? "warning" : "neutral"}
            detail={totalInjuries > 0 ? "Lineup alert" : "Clean slate"}
          />
        </div>
      )}

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

type StatusTone = "success" | "warning" | "info" | "neutral";

function StatusChip({
  label,
  detail,
  tone = "neutral",
}: {
  label: string;
  detail?: string;
  tone?: StatusTone;
}) {
  const toneStyles: Record<StatusTone, string> = {
    success: "border-emerald-500/60 bg-emerald-500/5 text-emerald-300",
    warning: "border-orange-500/60 bg-orange-500/5 text-orange-200",
    info: "border-sky-500/60 bg-sky-500/5 text-sky-200",
    neutral: "border-white/20 bg-white/5 text-white/70",
  };
  return (
    <div
      className={`inline-flex flex-col gap-0.5 rounded-full border px-4 py-1.5 text-[10px] font-semibold uppercase tracking-[0.3em] ${toneStyles[tone]}`}
    >
      <span className="text-[12px] font-bold uppercase tracking-[0.2em]">{label}</span>
      {detail && <span className="text-[9px] font-normal lowercase tracking-[0.15em] text-white/60">{detail}</span>}
    </div>
  );
}
