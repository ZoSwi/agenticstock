import { cn } from "@/lib/cn";

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "bullish" | "neutral" | "bearish" | "riskLow" | "riskMedium" | "riskHigh";
}) {
  const styles =
    tone === "bullish"
      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
      : tone === "bearish"
        ? "bg-rose-500/15 text-rose-700 dark:text-rose-300"
        : tone === "riskHigh"
          ? "bg-amber-500/15 text-amber-800 dark:text-amber-200"
          : tone === "riskMedium"
            ? "bg-indigo-500/15 text-indigo-800 dark:text-indigo-200"
            : tone === "riskLow"
              ? "bg-sky-500/15 text-sky-800 dark:text-sky-200"
              : "bg-black/5 text-black/70 dark:bg-white/10 dark:text-white/70";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium tracking-tight",
        styles,
        className
      )}
      {...props}
    />
  );
}

