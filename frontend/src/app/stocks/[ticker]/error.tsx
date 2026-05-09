"use client";

import Link from "next/link";

import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";

export default function StockError() {
  return (
    <Shell>
      <Card>
        <div className="text-base font-semibold">We hit an error loading this stock view</div>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">
          Please refresh the page. If this continues, check backend availability and API environment settings.
        </p>
        <div className="mt-4">
          <Link
            href="/"
            className="inline-block rounded-full border border-black/10 bg-white/60 px-4 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
          >
            Back to Home
          </Link>
        </div>
      </Card>
    </Shell>
  );
}
