"use client";

import { motion, AnimatePresence } from "framer-motion";

const STAGES = [
  { key: "market_data", label: "Market data" },
  { key: "news", label: "Recent news" },
  { key: "risk_factors", label: "Risk factors" },
  { key: "business_overview", label: "Business overview" },
];

export function PipelineTracker({
  done,
  active,
}: {
  done: Set<string>;
  active?: string | null;
}) {
  return (
    <div className="flex gap-3">
      {STAGES.map((stage) => {
        const isDone = done.has(stage.key);
        const isActive = !isDone && active === stage.key;
        return (
          <motion.div
            key={stage.key}
            animate={{ opacity: isDone || isActive ? 1 : 0.5 }}
            className="flex flex-1 flex-col gap-1 rounded-md border border-border bg-card px-3 py-2"
          >
            <span className="relative flex h-1.5 w-1.5 items-center justify-center">
              <AnimatePresence mode="wait" initial={false}>
                {isDone ? (
                  <motion.span
                    key="done"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500, damping: 20 }}
                    className="h-1.5 w-1.5 rounded-full bg-accent-green"
                  />
                ) : isActive ? (
                  <motion.span
                    key="active"
                    initial={{ scale: 0.6, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-green"
                  />
                ) : (
                  <motion.span
                    key="pending"
                    initial={{ scale: 0.6, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="h-1.5 w-1.5 rounded-full bg-muted-foreground"
                  />
                )}
              </AnimatePresence>
            </span>
            <span className="font-mono text-xs text-muted-foreground">{stage.label}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
