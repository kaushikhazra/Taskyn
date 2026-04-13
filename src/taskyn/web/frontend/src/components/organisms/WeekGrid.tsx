import { WeekDayCard } from '@/components/molecules/WeekDayCard';
import type { WeeklyDaySummary } from '@/types';

interface WeekGridProps {
  days: WeeklyDaySummary[];
  onDayClick: (date: string) => void;
}

export function WeekGrid({ days, onDayClick }: WeekGridProps) {
  return (
    <div className="week-grid">
      {days.map((daySummary) => (
        <WeekDayCard
          key={daySummary.date}
          daySummary={daySummary}
          onClick={onDayClick}
        />
      ))}
    </div>
  );
}
