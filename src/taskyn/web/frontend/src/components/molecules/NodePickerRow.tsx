import { useState } from 'react';
import { Button } from '@/components/atoms';
import { getNodeTypeUI } from '@/config/methodology-ui';
import type { Node } from '@/types';

interface NodePickerRowProps {
  node: Node;
  methodology: string;
  onAdd: (nodeId: string, plannedMinutes?: number) => void;
  disabled?: boolean;
}

export function NodePickerRow({ node, methodology, onAdd, disabled }: NodePickerRowProps) {
  const [minutes, setMinutes] = useState('');
  const [showMinutes, setShowMinutes] = useState(false);
  const typeUI = getNodeTypeUI(methodology, node.node_type);

  const handleAdd = () => {
    const parsed = minutes ? parseInt(minutes, 10) : undefined;
    onAdd(node.id, parsed && !isNaN(parsed) ? parsed : undefined);
    setMinutes('');
    setShowMinutes(false);
  };

  return (
    <div className="node-picker-row">
      <span className="badge badge-node-type" style={{ background: typeUI.color }}>
        {typeUI.icon}
      </span>
      <div className="node-picker-row__info">
        <span className="node-picker-row__title">{node.title}</span>
        <span className="node-picker-row__meta">{node.status}</span>
      </div>
      {showMinutes && (
        <input
          className="node-picker-row__minutes form-input"
          type="number"
          min="1"
          placeholder="min"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleAdd();
          }}
          autoFocus
        />
      )}
      <div className="node-picker-row__actions">
        {!showMinutes && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowMinutes(true)}
            disabled={disabled}
            title="Set planned minutes before adding"
          >
            min
          </Button>
        )}
        <Button
          variant="primary"
          size="sm"
          onClick={handleAdd}
          disabled={disabled}
        >
          + Add
        </Button>
      </div>
    </div>
  );
}
