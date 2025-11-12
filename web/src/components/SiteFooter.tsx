import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/5 bg-slate-950/80 px-6 py-8 text-sm text-white/60 lg:px-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <p>© {new Date().getFullYear()} Puckcast Analytics. Nightly NHL model updates + public notes.</p>
        <div className="flex flex-wrap gap-4 text-xs uppercase tracking-[0.4em]">
          <Link href="mailto:team@puckcast.ai" className="hover:text-white">
            Contact
          </Link>
          <Link href="https://github.com/noahowsh/puckcast" className="hover:text-white">
            GitHub
          </Link>
          <Link href="https://x.com/puckcastai" className="hover:text-white">
            Follow
          </Link>
        </div>
      </div>
    </footer>
  );
}
