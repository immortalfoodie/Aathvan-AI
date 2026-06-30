import { useState, useEffect } from "react";

export default function ReviewPlan({ task, steps, onApprove, onCancel }) {
  const [editableSteps, setEditableSteps] = useState([]);

  useEffect(() => {
    // Clone and sort the steps by order_index to make sure they display in order
    const sorted = [...steps].sort((a, b) => a.order_index - b.order_index);
    setEditableSteps(sorted);
  }, [steps]);

  const handleStepChange = (index, field, value) => {
    setEditableSteps((prev) =>
      prev.map((step, idx) => {
        if (idx !== index) return step;
        return {
          ...step,
          [field]: field === "estimated_hours" ? (value === "" ? "" : parseFloat(value) || 0) : value,
        };
      })
    );
  };

  const deleteStep = (index) => {
    setEditableSteps((prev) =>
      prev.filter((_, idx) => idx !== index).map((step, idx) => ({ ...step, order_index: idx }))
    );
  };

  const addStep = () => {
    setEditableSteps((prev) => [
      ...prev,
      {
        title: "",
        description: "",
        estimated_hours: 1.0,
        order_index: prev.length,
      },
    ]);
  };

  const moveStep = (index, direction) => {
    if (direction === "up" && index === 0) return;
    if (direction === "down" && index === editableSteps.length - 1) return;

    const swapWith = direction === "up" ? index - 1 : index + 1;
    const newSteps = [...editableSteps];
    
    // Swap the elements
    const temp = newSteps[index];
    newSteps[index] = newSteps[swapWith];
    newSteps[swapWith] = temp;

    // Update order_indexes
    const updated = newSteps.map((step, idx) => ({ ...step, order_index: idx }));
    setEditableSteps(updated);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Validate titles are not empty
    const invalid = editableSteps.some((s) => !s.title.trim());
    if (invalid) {
      alert("All steps must have a title.");
      return;
    }
    onApprove(editableSteps);
  };

  const totalEstimatedHours = editableSteps.reduce(
    (sum, step) => sum + (parseFloat(step.estimated_hours) || 0),
    0
  );

  return (
    <div className="review-plan-card" id="review-plan-section">
      <div className="review-plan-header">
        <h2>Review AI Suggested Plan</h2>
        <p className="task-summary-text">"{task.task_summary}"</p>
      </div>

      {task.ai_confidence_note && (
        <div className="confidence-callout">
          <span className="callout-icon">ℹ️</span>
          <div className="callout-content">
            <strong>Mentor Note:</strong> {task.ai_confidence_note}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="review-plan-form">
        <div className="proposed-steps-list">
          {editableSteps.map((step, index) => (
            <div key={index} className="editable-step-row" id={`edit-step-row-${index}`}>
              <div className="step-number-badge">{index + 1}</div>
              
              <div className="step-inputs">
                <input
                  type="text"
                  placeholder="Step title (required)"
                  value={step.title}
                  onChange={(e) => handleStepChange(index, "title", e.target.value)}
                  className="step-title-input-field"
                  required
                />
                <textarea
                  placeholder="Step description (optional)"
                  value={step.description || ""}
                  onChange={(e) => handleStepChange(index, "description", e.target.value)}
                  className="step-desc-input-field"
                  rows={2}
                />
                <div className="step-hours-wrapper">
                  <label>Estimate (hours):</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    placeholder="1.0"
                    value={step.estimated_hours}
                    onChange={(e) => handleStepChange(index, "estimated_hours", e.target.value)}
                    className="step-hours-input-field"
                  />
                </div>
              </div>

              <div className="step-actions-column">
                <div className="order-buttons">
                  <button
                    type="button"
                    className="btn-icon"
                    onClick={() => moveStep(index, "up")}
                    disabled={index === 0}
                    title="Move up"
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    className="btn-icon"
                    onClick={() => moveStep(index, "down")}
                    disabled={index === editableSteps.length - 1}
                    title="Move down"
                  >
                    ▼
                  </button>
                </div>
                <button
                  type="button"
                  className="btn btn-danger btn-sm delete-step-btn"
                  onClick={() => deleteStep(index)}
                  title="Delete step"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-full add-step-btn-review"
          onClick={addStep}
          id="review-add-step-btn"
        >
          + Add Step Manually
        </button>

        <div className="review-summary-row">
          <div className="total-hours-display">
            Total Estimated Time: <span>{totalEstimatedHours.toFixed(1)} hours</span>
          </div>
          <div className="review-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onCancel}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              id="approve-plan-submit-btn"
            >
              Approve Plan
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
