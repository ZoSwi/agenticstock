import { Suspense } from "react";

import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { CompareClient } from "@/app/compare/compare-client";

export default function ComparePage() {
  return (
    <Shell>
      <Suspense
        fallback={
          <Card>
            <div className="text-sm text-black/60 dark:text-white/60">Loading compare…</div>
          </Card>
        }
      >
        <CompareClient />
      </Suspense>
    </Shell>
  );
}

