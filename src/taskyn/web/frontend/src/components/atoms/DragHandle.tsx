interface DragHandleProps {
  disabled?: boolean;
  className?: string;
}

export function DragHandle({ disabled = false, className = '' }: DragHandleProps) {
  if (disabled) return null;

  return (
    <span className={`drag-handle ${className}`} aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        width={16}
        height={16}
        stroke="currentColor"
        fill="none"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="9" cy="6" r="1" fill="currentColor" />
        <circle cx="15" cy="6" r="1" fill="currentColor" />
        <circle cx="9" cy="12" r="1" fill="currentColor" />
        <circle cx="15" cy="12" r="1" fill="currentColor" />
        <circle cx="9" cy="18" r="1" fill="currentColor" />
        <circle cx="15" cy="18" r="1" fill="currentColor" />
      </svg>
    </span>
  );
}
