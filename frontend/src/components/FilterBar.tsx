interface FilterBarProps {
  value: string;
  onChange: (value: string) => void;
}

const filters = [
  { value: "", label: "All" },
  { value: "stop work", label: "Stop Work" },
  { value: "rectification", label: "Rectification" },
  { value: "prohibition", label: "Prohibition" },
];

export function FilterBar({ value, onChange }: FilterBarProps) {
  return (
    <div className="flex items-center gap-2">
      {filters.map((f) => {
        const active = value === f.value;
        return (
          <button
            key={f.value}
            onClick={() => onChange(f.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium border transition-colors ${
              active
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card text-foreground border-border hover:bg-accent"
            }`}
          >
            {f.label}
          </button>
        );
      })}
    </div>
  );
}
