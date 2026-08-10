"use client";

import { motion, AnimatePresence } from "framer-motion";

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
      <AnimatePresence mode="wait" initial={false}>
        {done ? (
          <motion.span
            key="done"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 20 }}
            className="h-1.5 w-1.5 rounded-full bg-accent-green"
          />
        ) : (
          <motion.span
            key="pending"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-green"
          />
        )}
      </AnimatePresence>
      <span>
        {tool}({JSON.stringify(args)})
      </span>
      {done && <span className="ml-auto text-accent-green">done</span>}
    </motion.div>
  );
}
