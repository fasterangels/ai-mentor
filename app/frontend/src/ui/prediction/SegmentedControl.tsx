import React from "react";

export interface SegmentedControlOption {
  value: string;
  label: string;
}

export interface SegmentedControlProps {
  value: string;
  options: SegmentedControlOption[];
  onChange?: (value: string) => void;
  "aria-label"?: string;
}

export default function SegmentedControl({
  value,
  options,
  onChange,
  "aria-label": ariaLabel,
}: SegmentedControlProps) {
  return (
    <div className="ai-segmented" role="tablist" aria-label={ariaLabel}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            className={`ai-segmented__option ${active ? "ai-segmented__option--active" : ""}`}
            onClick={() => {
              if (!active) onChange?.(opt.value);
            }}
            role="tab"
            aria-selected={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

