/**
 * Step item component — displays a step with status toggle.
 * When marking as done, shows an optional "hours spent?" quick input.
 */
import { useState } from "react";
import client from "../api/client";

const STATUS_CYCLE = ["pending", "in_progress", "done", "skipped"];

const STATUS_ICONS = {
  pending: "○",
  in_progress: "◐",
  done: "●",
  skipped: "⊘",
};

const STATUS_LABELS = {
  pending: "Pending",
  in_progress: "In Progress",
  done: "Done",
  skipped: "Skipped",
};

export default function StepItem({ step, onUpdate, onAllStepsUpdate }) {
  const [loading, setLoading] = useState(false);
  const [showHoursInput, setShowHoursInput] = useState(false);
  const [actualHours, setActualHours] = useState("");

  const getNextStatus = () => {
    const currentIdx = STATUS_CYCLE.indexOf(step.status);
    return STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
  };

  const cycleStatus = async () => {
    const nextStatus = getNextStatus();

    // If transitioning to done, show hours input first
    if (nextStatus === "done") {
      setShowHoursInput(true);
      return;
    }

    await updateStep({ status: nextStatus });
  };

  const updateStep = async (payload) => {
    setLoading(true);
    try {
      const res = await client.patch(`/steps/${step.id}`, payload);
      // The enhanced endpoint returns { step, all_steps, task_at_risk }
      if (res.data.step) {
        onUpdate(res.data.step);
        // If parent provided a callback for all steps, use it for real-time re-plan
        if (onAllStepsUpdate && res.data.all_steps) {
          onAllStepsUpdate(res.data.all_steps, res.data.task_at_risk);
        }
      } else {
        // Fallback for legacy response shape
        onUpdate(res.data);
      }
    } catch (err) {
      console.error("Failed to update step:", err);
    } finally {
      setLoading(false);
      setShowHoursInput(false);
      setActualHours("");
    }
  };

  const handleHoursSubmit = (e) => {
    e.preventDefault();
    const payload = { status: "done" };
    if (actualHours !== "" && !isNaN(parseFloat(actualHours))) {
      payload.actual_hours_spent = parseFloat(actualHours);
    }
    updateStep(payload);
  };

  const handleSkipHours = () => {
    updateStep({ status: "done" });
  };

  return (
    <div className={`step-item step-${step.status}`} id={`step-${step.id}`}>
      <button
        className="step-status-btn"
        onClick={cycleStatus}
        disabled={loading || showHoursInput}
        title={`Click to change status (current: ${STATUS_LABELS[step.status]})`}
      >
        <span className="step-icon">{STATUS_ICONS[step.status]}</span>
      </button>
      <div className="step-content">
        <span className={`step-title ${step.status === "done" ? "step-done-text" : ""}`}>
          {step.title}
        </span>
        {step.description && <p className="step-description">{step.description}</p>}
        <div className="step-meta-row">
          {step.estimated_hours && (
            <span className="step-estimate">~{step.estimated_hours}h</span>
          )}
          {step.actual_hours_spent && (
            <span className="step-actual-hours">✓ {step.actual_hours_spent}h actual</span>
          )}
        </div>
        {step.scheduled_date && (
          <div className="step-date-badge">
            📅 {new Date(step.scheduled_date).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}
          </div>
        )}

        {/* Hours input when marking done */}
        {showHoursInput && (
          <form className="hours-input-inline step-hours-form" onSubmit={handleHoursSubmit}>
            <span className="hours-label">How long did this take?</span>
            <input
              type="number"
              min="0"
              step="0.25"
              placeholder="Hours"
              value={actualHours}
              onChange={(e) => setActualHours(e.target.value)}
              autoFocus
              className="hours-input-field"
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
              Done
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={handleSkipHours}
              disabled={loading}
            >
              Skip
            </button>
          </form>
        )}
      </div>
      <span className={`step-status-badge badge badge-${step.status}`}>
        {STATUS_LABELS[step.status]}
      </span>
    </div>
  );
}
