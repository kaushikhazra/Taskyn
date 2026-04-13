import { usePlanVsActual } from '@/hooks/queries/usePlans';
import { PlanVsActualSummary } from '@/components/molecules/PlanVsActualSummary';
import { PlanVsActualRow, UnplannedRow } from '@/components/molecules/PlanVsActualRow';

interface PlanVsActualPanelProps {
  date: string;
  actor: string;
  visible: boolean;
}

export function PlanVsActualPanel({ date, actor, visible }: PlanVsActualPanelProps) {
  const { data, isLoading } = usePlanVsActual(date, actor);

  if (!visible) return null;

  return (
    <div className="pva-panel">
      <h3 className="pva-panel__heading">Plan vs Actual</h3>

      {isLoading ? (
        <div className="pva-panel__loading">Loading comparison...</div>
      ) : !data ? (
        <div className="pva-panel__empty">No data available.</div>
      ) : (
        <>
          <PlanVsActualSummary summary={data.summary} />

          {data.planned_items.length > 0 && (
            <div className="pva-panel__section">
              <div className="pva-panel__table-header">
                <span>Item</span>
                <span>Planned</span>
                <span>Actual</span>
                <span>Delta</span>
              </div>
              {data.planned_items.map((item, idx) => (
                <PlanVsActualRow key={item.node_id ?? idx} item={item} />
              ))}
            </div>
          )}

          {data.unplanned_items.length > 0 && (
            <div className="pva-panel__section">
              <h4 className="pva-panel__subheading">Unplanned Work</h4>
              {data.unplanned_items.map((item) => (
                <UnplannedRow key={item.node_id} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
