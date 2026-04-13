import { useCallback, useState, type DragEvent } from 'react';
import { PlanItemRow } from '@/components/molecules/PlanItemRow';
import type { PlanItemEnriched, PlanOutcome, PlanStatus } from '@/types';

interface PlanItemListProps {
  items: PlanItemEnriched[];
  planStatus: PlanStatus;
  onOutcomeChange: (itemId: string, outcome: PlanOutcome) => void;
  onNotesChange: (itemId: string, notes: string) => void;
  onMinutesChange: (itemId: string, minutes: number | null) => void;
  onRemove: (itemId: string) => void;
  onReorder: (itemId: string, newPosition: number) => void;
}

export function PlanItemList({
  items,
  planStatus,
  onOutcomeChange,
  onNotesChange,
  onMinutesChange,
  onRemove,
  onReorder,
}: PlanItemListProps) {
  const [dragItemId, setDragItemId] = useState<string | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const isCompleted = planStatus === 'completed';

  const handleDragStart = useCallback(
    (e: DragEvent, itemId: string) => {
      if (isCompleted) return;
      setDragItemId(itemId);
      e.dataTransfer.effectAllowed = 'move';
      // Required for Firefox
      e.dataTransfer.setData('text/plain', itemId);
    },
    [isCompleted],
  );

  const handleDragOver = useCallback(
    (e: DragEvent, index: number) => {
      if (isCompleted || dragItemId === null) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      setDropIndex(index);
    },
    [isCompleted, dragItemId],
  );

  const handleDragLeave = useCallback(() => {
    setDropIndex(null);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent, targetIndex: number) => {
      e.preventDefault();
      if (dragItemId === null) return;

      // +1: backend uses 1-based positions (F-05)
      onReorder(dragItemId, targetIndex + 1);
      setDragItemId(null);
      setDropIndex(null);
    },
    [dragItemId, onReorder],
  );

  const handleDragEnd = useCallback(() => {
    setDragItemId(null);
    setDropIndex(null);
  }, []);

  if (items.length === 0) {
    return (
      <div className="plan-item-list plan-item-list--empty">
        <p className="plan-item-list__empty-text">No items in this plan yet.</p>
      </div>
    );
  }

  return (
    <div className="plan-item-list">
      {items.map((item, index) => (
        <PlanItemRow
          key={item.id}
          item={item}
          planStatus={planStatus}
          index={index}
          isDragging={dragItemId === item.id}
          isDropTarget={dropIndex === index && dragItemId !== item.id}
          onOutcomeChange={onOutcomeChange}
          onNotesChange={onNotesChange}
          onMinutesChange={onMinutesChange}
          onRemove={onRemove}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onDragEnd={handleDragEnd}
        />
      ))}
    </div>
  );
}
