"use client";

import { motion } from "framer-motion";

const STAGES = [
  { key: "market_data", label: "Market data" },
  { key: "news", label: "Recent news" },
  { key: "risk_factors", label: "Risk factors" },
  { key: "business_overview", label: "Business overview" },
];

export function PipelineTracker({ done }: { done: Set<string> }) {
  return (
    <div className="flex gap-3">
      {STAGES.map((stage) => {
        const isDone = done.has(stage.key);
        return (
          <motion.div
            key={stage.key}
            animate={{ opacity: isDone ? 1 : 0.5 }}
            className="flex flex-1 flex-col gap-1 rounded-md border border-border bg-card px-3 py-2"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isDone ? "bg-accent-green" : "bg-muted-foreground"}`}
            />
            <span className="font-mono text-xs text-muted-foreground">{stage.label}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
