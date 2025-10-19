/**
 * EntityPill Component
 * 
 * A reusable pill/badge component for displaying extracted entities
 * with consistent styling and optional tooltips.
 */

export interface EntityPillProps {
  /** The entity label/value to display */
  label: string;
  /** Optional tooltip text (e.g., source file) */
  tooltip?: string;
  /** Visual style variant */
  variant?: "default" | "primary" | "success" | "warning" | "error" | "info";
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Click handler for interactive pills */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

const VARIANT_CLASSES: Record<string, string> = {
  default: "bg-dark-bg-secondary text-dark-text-primary border-dark-border",
  primary: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  success: "bg-green-500/10 text-green-400 border-green-500/20",
  warning: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
  info: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
};

const SIZE_CLASSES: Record<string, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2 py-1 text-xs",
  lg: "px-3 py-1.5 text-sm",
};

export function EntityPill({
  label,
  tooltip,
  variant = "default",
  size = "md",
  onClick,
  className = "",
}: EntityPillProps) {
  const variantClass = VARIANT_CLASSES[variant];
  const sizeClass = SIZE_CLASSES[size];
  const isInteractive = !!onClick;

  const commonProps = {
    className: `
      inline-flex items-center rounded border
      ${variantClass}
      ${sizeClass}
      ${isInteractive ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
      ${className}
    `.trim(),
    title: tooltip,
  };

  if (isInteractive && onClick) {
    return (
      <button
        {...commonProps}
        onClick={onClick}
        type="button"
      >
        {label}
      </button>
    );
  }

  return (
    <span {...commonProps}>
      {label}
    </span>
  );
}

export default EntityPill;
