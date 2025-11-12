import { buildTeamSnapshots, computeStandingsPowerScore, getCurrentStandings, groupMatchupsByDate, type MatchupSummary, type TeamSnapshot } from "@/lib/current";
import standingsSnapshot from "@/data/currentStandings.json";

const snapshots = buildTeamSnapshots();
const snapshotMap = new Map(snapshots.map((team) => [team.abbrev, team]));
const standings = getCurrentStandings();
const standingsMeta = standingsSnapshot as { generatedAt?: string };

type LeaderboardRow = {
  currentRank: number;
  standingsRank: number;
  movement: number;
  team: string;
  abbrev: string;
  record: string;
  points: number;
  goalDifferential: number;
  pointPctg: number;
  goalsForPerGame?: number;
  goalsAgainstPerGame?: number;
  powerScore: number;
  nextGame?: TeamSnapshot["nextGame"];
  overlay?: TeamSnapshot;
};

const rowsPreSort: LeaderboardRow[] = standings.map((standing) => {
  const snap = snapshotMap.get(standing.abbrev);
  const power = computeStandingsPowerScore(standing);
  const record = `${standing.wins}-${standing.losses}-${standing.ot}`;
  return {
    currentRank: 0,
    standingsRank: standing.rank,
    movement: 0,
    team: standing.team,
    abbrev: standing.abbrev,
    record,
    points: standing.points,
    goalDifferential: standing.goalDifferential,
    pointPctg: standing.pointPctg,
    goalsForPerGame: standing.goalsForPerGame,
    goalsAgainstPerGame: standing.goalsAgainstPerGame,
    powerScore: power,
    nextGame: snap?.nextGame,
    overlay: snap,
  };
});

const rankedRows = rowsPreSort
  .sort((a, b) => b.powerScore - a.powerScore)
  .map((row, idx) => ({
    ...row,
    currentRank: idx + 1,
    movement: row.standingsRank - (idx + 1),
  }));

const biggestBoost = rankedRows.reduce<LeaderboardRow | null>((best, row) => {
  if (row.movement <= 0) return best;
  if (!best || row.movement > best.movement) {
    return row;
  }
  return best;
}, null);

const biggestSlide = rankedRows.reduce<LeaderboardRow | null>((best, row) => {
  if (row.movement >= 0) return best;
  if (!best || row.movement < best.movement) {
    return row;
  }
  return best;
}, null);

const alignedClubs = rankedRows.filter((row) => Math.abs(row.movement) <= 1).length;

const leaderboardHighlights = [
  {
    label: "Power #1",
    value: rankedRows[0]?.team ?? "—",
    detail: rankedRows[0] ? `Week of ${leaderboardWeekLabel}` : "Awaiting slate",
  },
  {
    label: "Biggest riser",
    value: biggestBoost ? `${biggestBoost.team} (+${biggestBoost.movement})` : "—",
    detail: biggestBoost ? `Standings #${biggestBoost.standingsRank}` : "No change",
  },
  {
    label: "Biggest slide",
    value: biggestSlide ? `${biggestSlide.team} (-${Math.abs(biggestSlide.movement)})` : "—",
    detail: biggestSlide ? `Standings #${biggestSlide.standingsRank}` : "No change",
  },
  {
    label: "Aligned clubs",
    value: `${alignedClubs}/32`,
    detail: "±1 spot vs standings",
  },
];

const schedule = groupMatchupsByDate().slice(0, 3);

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const formatGameDate = (iso?: string) => {
  if (!iso) return "TBD";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(new Date(`${iso}T00:00:00Z`));
};

const computeWeekStart = (anchor: Date) => {
  const base = new Date(anchor);
  const day = base.getUTCDay();
  const diff = (day + 6) % 7;
  base.setUTCDate(base.getUTCDate() - diff);
  base.setUTCHours(0, 0, 0, 0);
  return base;
};

const weekAnchor = standingsMeta.generatedAt ? new Date(standingsMeta.generatedAt) : new Date();
const leaderboardWeekStart = computeWeekStart(weekAnchor);
const leaderboardWeekLabel = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(leaderboardWeekStart);

export default function LeaderboardsPage() {
  return (
    <div className="relative overflow-hidden">
      <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-6 pb-16 pt-8 lg:px-12">
        <header className="space-y-3">
          <p className="text-sm uppercase tracking-[0.4em] text-lime-300">Leaderboards</p>
          <h1 className="text-4xl font-semibold text-white">Power rankings for the 2025-26 grind.</h1>
          <p className="max-w-3xl text-base text-white/75">
            Scores lean on points, goal differential, tempo, and shot share. We lock a fresh table every Monday morning so the list represents the current week at a glance.
          </p>
          <p className="text-xs uppercase tracking-[0.4em] text-white/50">Week of {leaderboardWeekLabel}</p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {leaderboardHighlights.map((card) => (
            <div key={card.label} className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.4em] text-white/50">{card.label}</p>
              <p className="mt-3 text-2xl font-semibold text-white">{card.value}</p>
              <p className="text-xs uppercase tracking-[0.4em] text-white/60">{card.detail}</p>
            </div>
          ))}
        </section>

        <section className="rounded-[36px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/30">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <p className="text-sm uppercase tracking-[0.4em] text-white/60">Power rankings</p>
            <p className="text-xs uppercase tracking-[0.4em] text-white/40">Week of {leaderboardWeekLabel}</p>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="text-white/60">
                <tr>
                  <th className="py-3 pr-4 text-left">Model rank</th>
                  <th className="py-3 px-4 text-left">Team · standings</th>
                  <th className="py-3 px-4 text-left">Record</th>
                  <th className="py-3 px-4 text-left">Points</th>
                  <th className="py-3 px-4 text-left">Goal diff</th>
                  <th className="py-3 px-4 text-left">Power score</th>
                  <th className="py-3 px-4 text-left">Movement</th>
                  <th className="py-3 px-4 text-left">Model overlay</th>
                  <th className="py-3 px-4 text-left">Next game</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-white/80">
                {rankedRows.map((row) => (
                  <tr key={row.team}>
                    <td className="py-3 pr-4 font-semibold text-white">#{row.currentRank}</td>
                    <td className="py-3 px-4 font-semibold text-white">
                      <p>{row.team}</p>
                      <p className="text-xs uppercase tracking-[0.4em] text-white/40">Standings #{row.standingsRank}</p>
                    </td>
                    <td className="py-3 px-4">{row.record}</td>
                    <td className="py-3 px-4">{row.points}</td>
                    <td className="py-3 px-4">
                      {row.goalDifferential >= 0 ? "+" : ""}
                      {row.goalDifferential}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-white">
                        <p className="font-semibold">{row.powerScore}</p>
                        <p className="text-xs uppercase tracking-[0.4em] text-white/50">{pct(row.pointPctg)} pts pct</p>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-xs text-white/60">
                      <Movement movement={row.movement} />
                    </td>
                    <td className="py-3 px-4">
                      {row.overlay ? (
                        <div className="text-xs uppercase tracking-[0.4em] text-white/50">
                          {pct(row.overlay.avgProb)} win avg · {(row.overlay.avgEdge * 100).toFixed(1)} pts edge
                        </div>
                      ) : (
                        <p className="text-xs uppercase tracking-[0.4em] text-white/40">No current slate data</p>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {row.nextGame ? (
                        <div className="text-xs uppercase tracking-[0.4em] text-white/50">
                          {row.nextGame.opponent} · {formatGameDate(row.nextGame.date)} · {row.nextGame.startTimeEt ?? "TBD"}
                        </div>
                      ) : (
                        <p className="text-xs uppercase tracking-[0.4em] text-white/40">Idle on current slate</p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-[36px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/30">
          <p className="text-sm uppercase tracking-[0.4em] text-lime-300">Upcoming schedule</p>
          <div className="mt-6 space-y-6">
            {schedule.map((day) => (
              <DateGroup key={day.date} day={day} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function DateGroup({ day }: { day: MatchupSummary }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-[0.4em] text-white/60">{day.date}</p>
      <div className="mt-3 space-y-3">
        {day.games.map((game) => (
          <article key={game.id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <p className="text-sm font-semibold text-white">{game.label}</p>
            <p className="text-xs uppercase tracking-[0.4em] text-white/50">
              {game.startTimeEt ?? "TBD"} · Favorite {game.favorite} · Edge {(game.edge * 100).toFixed(1)} pts
            </p>
            <p className="mt-1 text-xs text-white/70">{game.summary}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function Movement({ movement }: { movement: number }) {
  if (movement > 0) {
    return (
      <div className="space-y-1">
        <span className="text-sm text-lime-300">▲ +{movement}</span>
        <p className="text-[0.6rem] uppercase tracking-[0.4em] text-white/40">Power boost</p>
      </div>
    );
  }
  if (movement < 0) {
    return (
      <div className="space-y-1">
        <span className="text-sm text-rose-300">▼ {Math.abs(movement)}</span>
        <p className="text-[0.6rem] uppercase tracking-[0.4em] text-white/40">Power dip</p>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <span className="text-sm text-white/70">●</span>
      <p className="text-[0.6rem] uppercase tracking-[0.4em] text-white/40">In sync</p>
    </div>
  );
}
