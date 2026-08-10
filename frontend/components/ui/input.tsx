import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground transition-colors duration-150 focus-visible:border-accent-green/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-green",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
