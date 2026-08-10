"use client";

import { motion } from "framer-motion";

export function ToolStep({
  tool,
  args,
  done,
}: {
  tool: string;
  args: Record<string, unknown>;
  done: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 font-mono text-xs text-muted-foreground"
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-accent-green ${done ? "" : "animate-pulse"}`} />
      <span>
        {tool}({JSON.stringify(args)})
      </span>
      {done && <span className="ml-auto text-accent-green">done</span>}
    </motion.div>
  );
}
