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
    <div className="min-w-0 rounded-md border border-border bg-card p-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
      <div className="font-mono text-xs tracking-wide text-muted-foreground">{label}</div>
      <div
        title={value}
        className={`truncate font-mono text-lg font-semibold ${
          delta === "up" ? "text-accent-green" : delta === "down" ? "text-accent-red" : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
