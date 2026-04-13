import { useState, useCallback } from 'react';

interface PlannedMinutesProps {
  minutes: number | null;
  editable?: boolean;
  onChange?: (minutes: number | null) => void;
  className?: string;
}

function formatMinutes(m: number | null): string {
  if (m === null || m === 0) return '--';
  if (m >= 60 && m % 60 === 0) return `${m / 60}h`;
  if (m >= 60) return `${Math.floor(m / 60)}h${m % 60}m`;
  return `${m}m`;
}

export function PlannedMinutes({
  minutes,
  editable = false,
  onChange,
  className = '',
}: PlannedMinutesProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const startEdit = useCallback(() => {
    if (!editable) return;
    setDraft(minutes !== null ? String(minutes) : '');
    setEditing(true);
  }, [editable, minutes]);

  const commitEdit = useCallback(() => {
    setEditing(false);
    if (!onChange) return;
    const trimmed = draft.trim();
    if (trimmed === '') {
      onChange(null);
    } else {
      const parsed = parseInt(trimmed, 10);
      if (!isNaN(parsed) && parsed >= 0) onChange(parsed);
    }
  }, [draft, onChange]);

  if (editing) {
    return (
      <input
        className={`planned-minutes planned-minutes--editing ${className}`}
        type="number"
        min={0}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commitEdit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commitEdit();
          if (e.key === 'Escape') setEditing(false);
        }}
        autoFocus
      />
    );
  }

  return (
    <span
      className={`planned-minutes ${editable ? 'planned-minutes--editable' : ''} ${className}`}
      onClick={startEdit}
      title={editable ? 'Click to edit' : undefined}
    >
      {formatMinutes(minutes)}
    </span>
  );
}
