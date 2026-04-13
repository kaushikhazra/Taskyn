import { useRef, useState } from 'react';
import { Icon } from '@/components/atoms';

interface OutcomeNotesProps {
  notes: string | null;
  onNotesChange: (notes: string) => void;
}

export function OutcomeNotes({ notes, onNotesChange }: OutcomeNotesProps) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState(notes ?? '');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const hasNotes = !!notes && notes.trim().length > 0;

  const handleToggle = () => {
    if (!expanded) {
      setDraft(notes ?? '');
      setExpanded(true);
      // Focus after next render
      requestAnimationFrame(() => inputRef.current?.focus());
    } else {
      // Save on collapse if changed
      const trimmed = draft.trim();
      if (trimmed !== (notes ?? '')) {
        onNotesChange(trimmed);
      }
      setExpanded(false);
    }
  };

  const handleBlur = () => {
    const trimmed = draft.trim();
    if (trimmed !== (notes ?? '')) {
      onNotesChange(trimmed);
    }
    setExpanded(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setDraft(notes ?? '');
      setExpanded(false);
    }
  };

  return (
    <div className="outcome-notes">
      <button
        type="button"
        className={`outcome-notes__toggle ${hasNotes ? 'outcome-notes__toggle--has-notes' : ''}`}
        onClick={handleToggle}
        title={hasNotes ? notes! : 'Add notes'}
        aria-expanded={expanded}
      >
        <Icon name="edit" size={14} />
      </button>

      {expanded && (
        <div className="outcome-notes__editor">
          <textarea
            ref={inputRef}
            className="outcome-notes__input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            placeholder="Add outcome notes..."
            rows={2}
          />
        </div>
      )}
    </div>
  );
}
