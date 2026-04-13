import { usePlannerParams } from '@/hooks/usePlannerParams';
import { PlannerToolbar } from '@/components/organisms/PlannerToolbar';
import { DayView } from '@/components/organisms/DayView';
import { WeekView } from '@/components/organisms/WeekView';
import { MonthView } from '@/components/organisms/MonthView';

export function PlannerPage() {
  const { view, date, actor, setView, setDate, setDateAndView } = usePlannerParams();

  const handleDateChange = (newDate: string, newView?: 'day') => {
    if (newView) {
      setDateAndView(newDate, newView);
    } else {
      setDate(newDate);
    }
  };

  return (
    <div className="content-wrapper">
      <div className="page-header">
        <h1 className="page-title">Planner</h1>
      </div>

      <PlannerToolbar
        date={date}
        view={view}
        onDateChange={setDate}
        onViewChange={setView}
      />

      {view === 'day' && (
        <DayView
          date={date}
          actor={actor}
          onNavigateToDate={(d) => handleDateChange(d, 'day')}
        />
      )}

      {view === 'week' && (
        <WeekView
          date={date}
          actor={actor}
          onDateChange={(d, v) => setDateAndView(d, v)}
        />
      )}

      {view === 'month' && (
        <MonthView
          date={date}
          actor={actor}
          onDateChange={(d, v) => setDateAndView(d, v)}
        />
      )}
    </div>
  );
}
