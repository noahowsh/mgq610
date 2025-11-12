import { buildTeamSnapshots, type TeamSnapshot } from "@/lib/current";

const snapshots = buildTeamSnapshots();

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

const topTeams = snapshots.slice(0, 8);
const underdogs = [...snapshots].sort((a, b) => a.avgProb - b.avgProb).slice(0, 6);

function bucketUpcomingGames(teams: TeamSnapshot[]) {
  const buckets = [
    { label: "0-5 pts edge", min: 0, max: 0.05, count: 0 },
    { label: "5-10 pts edge", min: 0.05, max: 0.1, count: 0 },
    { label: "10-15 pts edge", min: 0.1, max: 0.15, count: 0 },
    { label: "15-20 pts edge", min: 0.15, max: 0.2, count: 0 },
    { label: "20+ pts edge", min: 0.2, max: Infinity, count: 0 },
  ];

  const gamesPerTeam = teams.reduce((sum, team) => sum + team.games, 0);

  teams.forEach((team) => {
    buckets.forEach((bucket) => {
      if (team.avgEdge >= bucket.min && team.avgEdge < bucket.max) {
        bucket.count += team.games;
      }
    });
  });

  return { buckets, total: gamesPerTeam };
}

const edgeDistribution = bucketUpcomingGames(snapshots);

export default function PerformancePage() {
  return (
    <div className="relative overflow-hidden">
      <div className="relative mx-auto flex max-w-6xl flex-col gap-12 px-6 pb-16 pt-8 lg:px-12">
        <header className="space-y-3">
          <p className="text-sm uppercase tracking-[0.4em] text-lime-300">Performance analytics</p>
          <h1 className="text-4xl font-semibold text-white">Upcoming slate focus.</h1>
          <p className="max-w-3xl text-base text-white/75">
            These tables summarize the teams and games on tonight&apos;s slate. Historical accuracy and calibration now live on the
            Analytics page.
          </p>
        </header>

        <section className="rounded-[36px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/30">
          <p className="text-sm uppercase tracking-[0.4em] text-white/60">Teams with the highest model confidence</p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="text-white/60">
                <tr>
                  <th className="py-3 pr-4 text-left">Team</th>
                  <th className="py-3 px-4 text-left">Record</th>
                  <th className="py-3 px-4 text-left">Games listed</th>
                  <th className="py-3 px-4 text-left">Avg win %</th>
                  <th className="py-3 px-4 text-left">Avg edge</th>
                  <th className="py-3 px-4 text-left">Favorite rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-white/80">
                {topTeams.map((team) => (
                  <tr key={team.team}>
                    <td className="py-3 pr-4 font-semibold text-white">{team.team}</td>
                    <td className="py-3 px-4 text-white/70">{team.record ?? "—"}</td>
                    <td className="py-3 px-4">{team.games}</td>
                    <td className="py-3 px-4">{pct(team.avgProb)}</td>
                    <td className="py-3 px-4">{(team.avgEdge * 100).toFixed(1)} pts</td>
                    <td className="py-3 px-4">{pct(team.favoriteRate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[36px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/30">
            <p className="text-sm uppercase tracking-[0.4em] text-white/60">Edge distribution across upcoming games</p>
            <div className="mt-4 space-y-4">
              {edgeDistribution.buckets.map((bucket) => (
                <div key={bucket.label}>
                  <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-white/60">
                    <span>{bucket.label}</span>
                    <span>{bucket.count} slots</span>
                  </div>
                  <div className="mt-2 h-2.5 w-full rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-lime-300 via-emerald-400 to-cyan-300"
                      style={{ width: edgeDistribution.total ? `${(bucket.count / edgeDistribution.total) * 100}%` : "0%" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-[36px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-black/30">
            <p className="text-sm uppercase tracking-[0.4em] text-white/60">Teams we&apos;re watching</p>
            <div className="mt-4 space-y-4">
              {underdogs.map((team) => (
                <article key={team.team} className="rounded-3xl border border-white/10 bg-black/20 p-4">
                  <p className="text-sm font-semibold text-white">{team.team}</p>
                  <p className="text-xs uppercase tracking-[0.4em] text-white/50">
                    {team.games} games · avg win {pct(team.avgProb)} · avg edge {(team.avgEdge * 100).toFixed(1)} pts
                  </p>
                  <p className="mt-2 text-xs text-white/70">
                    {team.nextGame ? `Next: ${team.nextGame.opponent} on ${team.nextGame.date}` : "No games listed"}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
