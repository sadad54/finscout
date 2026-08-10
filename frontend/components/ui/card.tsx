import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-lg border border-t-white/5 border-border bg-card p-4 shadow-lg shadow-black/40 transition-all duration-200",
        className
      )}
      {...props}
    />
  );
}
