"use client";

import * as React from "react";

import { cn } from "@/lib/cn";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-2xl border border-black/10 bg-white/70 px-4 text-sm outline-none backdrop-blur placeholder:text-black/35 focus:ring-2 focus:ring-indigo-500/25 dark:border-white/10 dark:bg-white/5 dark:placeholder:text-white/35",
        className
      )}
      {...props}
    />
  );
}

