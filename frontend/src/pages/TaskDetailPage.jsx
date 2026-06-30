/**
 * Task detail page — shows task info and its steps.
 * Handles AI plan generation, review, and approval flow.
 * Step 3: Real-time schedule updates on step status changes + at-risk banner.
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import StepItem from "../components/StepItem";
import ReviewPlan from "../components/ReviewPlan";
import { useAuth } from "../contexts/AuthContext";

const STATUS_OPTIONS = [
  { value: "not_started", label: "Not Started" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
];

const TYPE_LABELS = {
  assignment: "Assignment",
  project: "Project",
  bill: "Bill",
  application: "Application",
  personal_goal: "Personal Goal",
  other: "Other",
};

export default function TaskDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [task, setTask] = useState(null);
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newStep, setNewStep] = useState({ title: "", description: "" });
  const [addingStep, setAddingStep] = useState(false);
  const [showStepForm, setShowStepForm] = useState(false);
  const [taskAtRisk, setTaskAtRisk] = useState(false);

  // AI-specific state
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [syncingCalendar, setSyncingCalendar] = useState(false);

  const handleSyncCalendar = async () => {
    setSyncingCalendar(true);
    try {
      const res = await client.post(`/tasks/${id}/sync-calendar`);
      setSteps(res.data.steps);
      alert("Successfully synchronized schedule with Google Calendar!");
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to sync with Google Calendar.";
      alert(msg);
    } finally {
      setSyncingCalendar(false);
    }
  };

  const fetchTask = useCallback(async () => {
    try {
      const [taskRes, stepsRes] = await Promise.all([
        client.get(`/tasks/${id}`),
        client.get(`/tasks/${id}/steps`),
      ]);
      setTask(taskRes.data);
      setSteps(stepsRes.data);
    } catch (err) {
      if (err.response?.status === 404) {
        navigate("/");
      }
      console.error("Failed to fetch task:", err);
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  const handleStatusChange = async (newStatus) => {
    try {
      const res = await client.patch(`/tasks/${id}`, { status: newStatus });
      setTask(res.data);
    } catch (err) {
      console.error("Failed to update task status:", err);
    }
  };

  const handleAddStep = async (e) => {
    e.preventDefault();
    if (!newStep.title.trim()) return;
    setAddingStep(true);
    try {
      await client.post(`/tasks/${id}/steps`, {
        title: newStep.title.trim(),
        description: newStep.description.trim() || null,
        order_index: steps.length,
      });
      setNewStep({ title: "", description: "" });
      setShowStepForm(false);
      await fetchTask();
    } catch (err) {
      console.error("Failed to add step:", err);
    } finally {
      setAddingStep(false);
    }
  };

  const handleStepUpdate = (updatedStep) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === updatedStep.id ? updatedStep : s))
    );
  };

  // Called when the PATCH response includes re-planned sibling steps
  const handleAllStepsUpdate = (allSteps, atRisk) => {
    setSteps(allSteps);
    setTaskAtRisk(atRisk);
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this task and all its steps?")) return;
    try {
      await client.delete(`/tasks/${id}`);
      navigate("/");
    } catch (err) {
      console.error("Failed to delete task:", err);
    }
  };

  // AI action handlers
  const handleGeneratePlan = async () => {
    setGeneratingPlan(true);
    setAiError(null);
    try {
      await client.post(`/tasks/${id}/generate-plan`);
      await fetchTask();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to generate AI plan. Please check settings.";
      setAiError(msg);
    } finally {
      setGeneratingPlan(false);
    }
  };

  const handleApprovePlan = async (finalSteps) => {
    setLoading(true);
    setAiError(null);
    try {
      await client.post(`/tasks/${id}/approve-plan`, { steps: finalSteps });
      await fetchTask();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to approve plan.";
      setAiError(msg);
      setLoading(false);
    }
  };

  const handleCancelPlan = async () => {
    setLoading(true);
    try {
      await client.patch(`/tasks/${id}`, { ai_plan_status: "not_generated" });
      await fetchTask();
    } catch (err) {
      console.error("Failed to cancel plan:", err);
      setLoading(false);
    }
  };

  const handleRegeneratePlan = async () => {
    const confirm = window.confirm(
      "Regenerating the plan will delete all current steps and re-run AI generation. Are you sure you want to redo it?"
    );
    if (!confirm) return;
    await handleGeneratePlan();
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
      </div>
    );
  }

  if (!task) return null;

  const dueDate = task.due_date
    ? new Date(task.due_date).toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null;

  const completedSteps = steps.filter((s) => s.status === "done").length;

  return (
    <div className="task-detail" id="task-detail-page">
      {/* Back button */}
      <button className="back-link" onClick={() => navigate("/")}>
        ← Back to Dashboard
      </button>

      {/* Task header */}
      <div className="task-detail-header">
        <div className="task-detail-title-row">
          <h1>{task.title}</h1>
          <button className="btn btn-danger btn-sm" onClick={handleDelete} id="delete-task-btn">
            Delete Task
          </button>
        </div>

        <div className="task-detail-meta">
          <span className="task-type-tag">{TYPE_LABELS[task.task_type] || "Other"}</span>
          {dueDate && <span className="task-due">📅 Due: {dueDate}</span>}
          <div className="task-status-select">
            <label htmlFor="task-status">Status:</label>
            <select
              id="task-status"
              value={task.status}
              onChange={(e) => handleStatusChange(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {task.raw_description && (
          <div className="task-detail-description">
            <h3>Description</h3>
            <p>{task.raw_description}</p>
          </div>
        )}
      </div>

      {/* At-risk banner */}
      {taskAtRisk && task.ai_plan_status === "approved" && (
        <div className="at-risk-banner detail-at-risk" id="detail-at-risk-banner">
          ⚠️ This task now needs more time per day than originally planned to finish by the deadline.
          Consider adjusting the scope or deadline.
        </div>
      )}

      {/* Error callout if plan generation fails */}
      {aiError && (
        <div className="form-error" style={{ marginBottom: "24px", padding: "16px" }} id="ai-error-banner">
          <strong>Plan Generation Error:</strong> {aiError}
        </div>
      )}

      {/* AI loading state */}
      {generatingPlan && (
        <div className="ai-loading-container" id="ai-loading-screen">
          <div className="brain-icon-pulse">⚡🧠⚡</div>
          <div className="ai-loading-text">Generating Actionable Steps...</div>
          <div className="ai-loading-subtext">Claude is breaking down this task and estimating effort. Please wait.</div>
        </div>
      )}

      {/* Plan generation states */}
      {!generatingPlan && task.ai_plan_status === "not_generated" && (
        <div className="ai-loading-container" style={{ border: "2px dashed var(--color-border-light)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "12px" }}>🤖</div>
          <h3>Need a breakdown?</h3>
          <p style={{ color: "var(--color-text-secondary)", marginBottom: "20px" }}>
            Let AI break this task down into realistic daily steps and time estimates.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleGeneratePlan}
            id="generate-plan-btn"
          >
            ✨ Generate AI Plan
          </button>
        </div>
      )}

      {!generatingPlan && task.ai_plan_status === "pending_approval" && (
        <ReviewPlan
          task={task}
          steps={steps}
          onApprove={handleApprovePlan}
          onCancel={handleCancelPlan}
        />
      )}

      {!generatingPlan && task.ai_plan_status === "approved" && (
        <div className="steps-section">
          <div className="steps-header">
            <h2>
              Steps
              {steps.length > 0 && (
                <span className="steps-count">
                  {completedSteps}/{steps.length} done
                </span>
              )}
            </h2>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {user?.google_connected && (
                <button
                  onClick={handleSyncCalendar}
                  disabled={syncingCalendar}
                  className="calendar-sync-btn btn btn-sm bg-neutral-900 border border-neutral-700 text-neutral-300 hover:text-white"
                  id="sync-calendar-btn"
                >
                  {syncingCalendar
                    ? "⏳ Syncing..."
                    : steps.some((s) => s.calendar_event_id)
                    ? "✓ Calendar Synced"
                    : "📅 Sync to Calendar"}
                </button>
              )}
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowStepForm(!showStepForm)}
                id="add-step-btn"
              >
                + Add Step
              </button>
              <button
                className="regenerate-plan-trigger"
                onClick={handleRegeneratePlan}
                id="regenerate-plan-btn"
              >
                🔄 Regenerate Plan
              </button>
            </div>
          </div>

          {/* Progress bar */}
          {steps.length > 0 && (
            <div className="steps-progress">
              <div
                className="steps-progress-bar"
                style={{ width: `${(completedSteps / steps.length) * 100}%` }}
              />
            </div>
          )}

          {/* Add step form */}
          {showStepForm && (
            <form onSubmit={handleAddStep} className="add-step-form">
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Step title"
                  value={newStep.title}
                  onChange={(e) => setNewStep({ ...newStep, title: e.target.value })}
                  autoFocus
                  id="step-title-input"
                />
              </div>
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Description (optional)"
                  value={newStep.description}
                  onChange={(e) =>
                    setNewStep({ ...newStep, description: e.target.value })
                  }
                  id="step-description-input"
                />
              </div>
              <div className="add-step-actions">
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={addingStep}
                  id="save-step-btn"
                >
                  {addingStep ? "Adding…" : "Add"}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowStepForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Steps list */}
          {steps.length === 0 ? (
            <div className="empty-steps">
              <p>No steps yet.</p>
            </div>
          ) : (
            <div className="steps-list">
              {steps.map((step) => (
                <StepItem
                  key={step.id}
                  step={step}
                  onUpdate={handleStepUpdate}
                  onAllStepsUpdate={handleAllStepsUpdate}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
