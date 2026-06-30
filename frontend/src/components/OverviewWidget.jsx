/**
 * OverviewWidget — compact "at a glance" display of all active tasks.
 * Shows urgency dots, mini progress bars, and days until due.
 */
import { useNavigate } from "react-router-dom";

function urgencyTier(score) {
  if (score > 2.5) return { dot: "🔴", className: "urgency-high" };
  if (score >= 1.0) return { dot: "🟡", className: "urgency-medium" };
  return { dot: "🟢", className: "urgency-low" };
}

export default function OverviewWidget({ items }) {
  const navigate = useNavigate();

  if (!items || items.length === 0) return null;

  return (
    <div className="overview-widget" id="overview-widget">
      <h2 className="overview-title">📊 At a Glance</h2>
      <div className="overview-grid">
        {items.map((item) => {
          const tier = urgencyTier(item.urgency_score);
          const progress = item.total_steps > 0
            ? (item.completed_steps / item.total_steps) * 100
            : 0;
          const daysInt = Math.round(item.days_until_due);
          const isOverdue = item.days_until_due <= 0;

          return (
            <button
              key={item.task_id}
              className={`overview-row ${tier.className} ${item.at_risk ? "overview-at-risk" : ""}`}
              onClick={() => navigate(`/tasks/${item.task_id}`)}
              id={`overview-${item.task_id}`}
            >
              <span className="urgency-dot">{tier.dot}</span>
              <div className="overview-info">
                <span className="overview-task-name">{item.task_title}</span>
                <div className="overview-progress-bar-wrapper">
                  <div
                    className="overview-progress-fill"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
              <div className="overview-stats">
                <span className="overview-progress-text">
                  {item.completed_steps}/{item.total_steps}
                </span>
                <span className={`overview-due ${isOverdue ? "overview-overdue" : ""}`}>
                  {isOverdue ? "Overdue" : `${daysInt}d left`}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
