export function StatTile({
  label,
  value,
  delta,
}: {
  label: string;
  value: string;
  delta?: "up" | "down";
}) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <div className="font-mono text-xs text-muted-foreground">{label}</div>
      <div
        className={`font-mono text-lg font-semibold ${
          delta === "up" ? "text-accent-green" : delta === "down" ? "text-accent-red" : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
