/**
 * ProgressBar Component
 * 
 * A reusable progress bar with animated fill and optional label.
 * Supports multiple variants for different use cases (confidence, completion, etc.)
 */

import { useRef, useEffect } from "react";

export interface ProgressBarProps {
  /** Current value (0-max range) */
  value: number;
  /** Maximum value (default: 100) */
  max?: number;
  /** Visual style variant */
  variant?: "primary" | "success" | "warning" | "error" | "info";
  /** Show percentage label */
  showLabel?: boolean;
  /** Custom label format function */
  formatLabel?: (value: number, max: number) => string;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional CSS classes */
  className?: string;
}

const VARIANT_GRADIENTS: Record<string, string> = {
  primary: "bg-gradient-to-r from-blue-500 to-cyan-500",
  success: "bg-gradient-to-r from-green-500 to-emerald-500",
  warning: "bg-gradient-to-r from-yellow-500 to-orange-500",
  error: "bg-gradient-to-r from-red-500 to-rose-500",
  info: "bg-gradient-to-r from-sky-500 to-blue-500",
};

const SIZE_CLASSES: Record<string, { bar: string; text: string }> = {
  sm: { bar: "h-1", text: "text-xs" },
  md: { bar: "h-2", text: "text-sm" },
  lg: { bar: "h-3", text: "text-base" },
};

export function ProgressBar({
  value,
  max = 100,
  variant = "primary",
  showLabel = true,
  formatLabel,
  size = "md",
  className = "",
}: ProgressBarProps) {
  const barRef = useRef<HTMLDivElement | null>(null);

  // Animate the progress bar width
  useEffect(() => {
    if (barRef.current) {
      const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
      barRef.current.style.width = `${percentage}%`;
    }
  }, [value, max]);

  const percentage = Math.round((value / max) * 100);
  const label = formatLabel ? formatLabel(value, max) : `${percentage}%`;
  const gradient = VARIANT_GRADIENTS[variant];
  const sizes = SIZE_CLASSES[size];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div 
        className={`flex-1 ${sizes.bar} bg-dark-bg-secondary rounded-full overflow-hidden`}
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          ref={barRef}
          className={`h-full ${gradient} transition-all duration-300`}
        />
      </div>
      {showLabel && (
        <span className={`${sizes.text} font-semibold text-dark-text-primary whitespace-nowrap`}>
          {label}
        </span>
      )}
    </div>
  );
}

export default ProgressBar;
