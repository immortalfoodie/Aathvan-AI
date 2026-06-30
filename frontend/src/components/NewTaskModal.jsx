/**
 * Modal for creating a new task.
 */
import { useState } from "react";

const TASK_TYPES = [
  { value: "other", label: "Other" },
  { value: "assignment", label: "Assignment" },
  { value: "project", label: "Project" },
  { value: "bill", label: "Bill" },
  { value: "application", label: "Application" },
  { value: "personal_goal", label: "Personal Goal" },
];

export default function NewTaskModal({ onClose, onSubmit }) {
  const [form, setForm] = useState({
    title: "",
    raw_description: "",
    task_type: "other",
    due_date: "",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) {
      setError("Title is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        title: form.title.trim(),
        raw_description: form.raw_description.trim() || null,
        task_type: form.task_type,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
      };
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create task");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} id="new-task-modal">
        <div className="modal-header">
          <h2>New Task</h2>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="form-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="task-title">Title *</label>
            <input
              id="task-title"
              name="title"
              type="text"
              value={form.title}
              onChange={handleChange}
              placeholder="What do you need to get done?"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="task-description">Description</label>
            <textarea
              id="task-description"
              name="raw_description"
              value={form.raw_description}
              onChange={handleChange}
              placeholder="Paste your assignment details, syllabus section, or any notes…"
              rows={4}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="task-type">Type</label>
              <select
                id="task-type"
                name="task_type"
                value={form.task_type}
                onChange={handleChange}
              >
                {TASK_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="task-due-date">Due Date</label>
              <input
                id="task-due-date"
                name="due_date"
                type="date"
                value={form.due_date}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
              id="create-task-btn"
            >
              {submitting ? "Creating…" : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
