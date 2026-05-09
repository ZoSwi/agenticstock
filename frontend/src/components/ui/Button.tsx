"use client";

import * as React from "react";

import { cn } from "@/lib/cn";

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  const base =
    "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-500/40 disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-black text-white hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/85"
      : variant === "secondary"
        ? "border border-black/10 bg-white hover:bg-black/5 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
        : "bg-transparent hover:bg-black/5 dark:hover:bg-white/10";
  return <button className={cn(base, styles, className)} {...props} />;
}

