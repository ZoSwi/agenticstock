import Link from "next/link";

import { ModeToggle } from "@/components/ModeToggle";
import { cn } from "@/lib/cn";

export function Shell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-h-dvh bg-transparent text-black dark:text-white", className)}>
      <header className="sticky top-0 z-30 border-b border-black/8 bg-white/70 backdrop-blur-xl dark:border-white/10 dark:bg-[#060b14]/75">
        <div className="mx-auto flex h-14 w-full max-w-[1400px] items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-sm font-semibold tracking-[0.02em]">
              AgenticPI Markets
            </Link>
            <nav className="hidden items-center gap-2 text-sm text-black/70 dark:text-white/70 md:flex">
              <Link href="/dashboard" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                Dashboard
              </Link>
              <Link href="/compare" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                Compare
              </Link>
              <Link href="/chat" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                AI Chat
              </Link>
              <Link href="/watchlist" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                Watchlist
              </Link>
              <Link href="/portfolio" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                Portfolio
              </Link>
              <Link href="/profile" className="rounded-full px-3 py-1.5 hover:bg-black/5 hover:text-black dark:hover:bg-white/10 dark:hover:text-white">
                Profile
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <ModeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] px-6 py-6">{children}</main>
    </div>
  );
}
