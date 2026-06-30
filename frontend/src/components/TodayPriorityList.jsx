/**
 * TodayPriorityList — ranked "what to work on next" across all tasks.
 * Each card shows the parent task, next step, urgency reason, and quick actions.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";

const STATUS_ICONS = {
  pending: "○",
  in_progress: "◐",
  done: "●",
};

export default function TodayPriorityList({ items, onUpdate }) {
  if (!items || items.length === 0) {
    return (
      <div className="today-empty" id="today-empty">
        <div className="today-empty-icon">🎉</div>
        <h3>All caught up!</h3>
        <p>No actionable steps right now. Create tasks and generate AI plans to get started.</p>
      </div>
    );
  }

  return (
    <div className="priority-list" id="priority-list">
      {items.map((item, idx) => (
        <PriorityCard
          key={item.task_id}
          item={item}
          rank={idx + 1}
          onUpdate={onUpdate}
        />
      ))}
    </div>
  );
}

function PriorityCard({ item, rank, onUpdate }) {
  const navigate = useNavigate();
  const [acting, setActing] = useState(false);
  const [showHoursInput, setShowHoursInput] = useState(false);
  const [actualHours, setActualHours] = useState("");

  const step = item.next_step;
  if (!step) return null;

  const handleMarkInProgress = async () => {
    setActing(true);
    try {
      await client.patch(`/steps/${step.id}`, { status: "in_progress" });
      onUpdate();
    } catch (err) {
      console.error("Failed to update step:", err);
    } finally {
      setActing(false);
    }
  };

  const handleMarkDone = async (hours = null) => {
    setActing(true);
    try {
      const payload = { status: "done" };
      if (hours !== null && hours !== "") {
        payload.actual_hours_spent = parseFloat(hours);
      }
      await client.patch(`/steps/${step.id}`, payload);
      setShowHoursInput(false);
      setActualHours("");
      onUpdate();
    } catch (err) {
      console.error("Failed to update step:", err);
    } finally {
      setActing(false);
    }
  };

  const handleDoneClick = () => {
    setShowHoursInput(true);
  };

  const handleHoursSubmit = (e) => {
    e.preventDefault();
    handleMarkDone(actualHours);
  };

  const handleSkipHours = () => {
    handleMarkDone(null);
  };

  return (
    <div
      className={`priority-card ${item.at_risk ? "priority-card-at-risk" : ""}`}
      id={`priority-card-${item.task_id}`}
    >
      {item.at_risk && (
        <div className="at-risk-banner" id={`at-risk-${item.task_id}`}>
          ⚠️ This task needs more time per day than originally planned to finish by the deadline
        </div>
      )}

      <div className="priority-card-header">
        <div className="priority-rank">#{rank}</div>
        <div className="priority-task-info">
          <button
            className="priority-task-title"
            onClick={() => navigate(`/tasks/${item.task_id}`)}
          >
            {item.task_title}
          </button>
          <div className="priority-reason">{item.reason}</div>
        </div>
        <div className="priority-score-badge">
          {item.urgency_score.toFixed(1)}
        </div>
      </div>

      <div className="priority-step-row">
        <span className="priority-step-icon">
          {STATUS_ICONS[step.status] || "○"}
        </span>
        <div className="priority-step-info">
          <span className="priority-step-title">{step.title}</span>
          {step.estimated_hours && (
            <span className="priority-step-estimate">~{step.estimated_hours}h</span>
          )}
        </div>

        {!showHoursInput ? (
          <div className="priority-actions">
            {step.status === "pending" && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleMarkInProgress}
                disabled={acting}
              >
                ▶ Start
              </button>
            )}
            <button
              className="btn btn-primary btn-sm"
              onClick={handleDoneClick}
              disabled={acting}
            >
              ✓ Done
            </button>
          </div>
        ) : (
          <form className="hours-input-inline" onSubmit={handleHoursSubmit}>
            <input
              type="number"
              min="0"
              step="0.25"
              placeholder="Hours?"
              value={actualHours}
              onChange={(e) => setActualHours(e.target.value)}
              autoFocus
              className="hours-input-field"
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={acting}>
              Save
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={handleSkipHours}
              disabled={acting}
            >
              Skip
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
