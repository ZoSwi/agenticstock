"use client";

import * as React from "react";

import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";

type Experience = "beginner" | "intermediate" | "advanced";
type Risk = "low" | "medium" | "high";

export default function ProfilePage() {
  const [experience, setExperience] = React.useState<Experience>("beginner");
  const [risk, setRisk] = React.useState<Risk>("medium");

  React.useEffect(() => {
    const e = (localStorage.getItem("experience") as Experience) || "beginner";
    const r = (localStorage.getItem("risk") as Risk) || "medium";
    setExperience(e);
    setRisk(r);
  }, []);

  React.useEffect(() => {
    localStorage.setItem("experience", experience);
  }, [experience]);
  React.useEffect(() => {
    localStorage.setItem("risk", risk);
  }, [risk]);

  return (
    <Shell>
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Profile</h2>
        <p className="mt-1 text-sm text-black/60 dark:text-white/60">
          Personalize explanations and risk posture. Stored locally in your browser for now.
        </p>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Card>
          <div className="text-sm font-medium">Experience</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(["beginner", "intermediate", "advanced"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setExperience(v)}
                className={
                  experience === v
                    ? "rounded-full bg-black px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-black"
                    : "rounded-full border border-black/10 bg-white/60 px-4 py-2 text-sm text-black/70 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-white/70 dark:hover:bg-white/10"
                }
              >
                {v}
              </button>
            ))}
          </div>
        </Card>
        <Card>
          <div className="text-sm font-medium">Risk level</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(["low", "medium", "high"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setRisk(v)}
                className={
                  risk === v
                    ? "rounded-full bg-black px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-black"
                    : "rounded-full border border-black/10 bg-white/60 px-4 py-2 text-sm text-black/70 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-white/70 dark:hover:bg-white/10"
                }
              >
                {v}
              </button>
            ))}
          </div>
          <div className="mt-4 text-xs text-black/50 dark:text-white/50">
            This setting can be used to adjust guidance rules and alerting thresholds.
          </div>
        </Card>
      </div>
    </Shell>
  );
}

