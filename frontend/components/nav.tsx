"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Ask" },
  { href: "/research", label: "Research Brief" },
];

export function Nav() {
  const pathname = usePathname();
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const ok = await checkHealth();
      if (!cancelled) setHealthy(ok);
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <nav className="flex items-center justify-between border-b border-border px-6 py-4">
      <div className="flex items-center gap-6">
        <span className="font-mono text-sm font-semibold tracking-tight text-accent-green">
          FinScout
        </span>
        {LINKS.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "relative pb-1 text-sm transition-colors hover:text-foreground",
                isActive ? "text-foreground" : "text-muted-foreground"
              )}
            >
              {link.label}
              {isActive && (
                <motion.div
                  layoutId="nav-underline"
                  className="absolute -bottom-[1px] left-0 right-0 h-[2px] rounded-full bg-accent-green"
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
            </Link>
          );
        })}
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span
          className={cn(
            "h-2 w-2 rounded-full transition-colors duration-300",
            healthy === null
              ? "bg-muted-foreground"
              : healthy
                ? "bg-accent-green shadow-[0_0_8px_rgba(36,194,121,0.6)]"
                : "bg-accent-red"
          )}
        />
        {healthy === null ? "connecting…" : healthy ? "backend online" : "backend unreachable"}
      </div>
    </nav>
  );
}
