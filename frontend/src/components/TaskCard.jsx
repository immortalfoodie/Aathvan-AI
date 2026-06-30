/**
 * Task card for the dashboard list.
 */
import { useNavigate } from "react-router-dom";

const STATUS_CONFIG = {
  not_started: { label: "Not Started", className: "badge-neutral" },
  in_progress: { label: "In Progress", className: "badge-info" },
  completed: { label: "Completed", className: "badge-success" },
};

const TYPE_LABELS = {
  assignment: "Assignment",
  project: "Project",
  bill: "Bill",
  application: "Application",
  personal_goal: "Personal Goal",
  other: "Other",
};

export default function TaskCard({ task }) {
  const navigate = useNavigate();
  const status = STATUS_CONFIG[task.status] || STATUS_CONFIG.not_started;

  const dueDate = task.due_date
    ? new Date(task.due_date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  const isOverdue =
    task.due_date &&
    task.status !== "completed" &&
    new Date(task.due_date) < new Date();

  return (
    <button
      className="task-card"
      onClick={() => navigate(`/tasks/${task.id}`)}
      id={`task-card-${task.id}`}
    >
      <div className="task-card-header">
        <h3 className="task-card-title">{task.title}</h3>
        <span className={`badge ${status.className}`}>{status.label}</span>
      </div>

      {task.raw_description && (
        <p className="task-card-desc">
          {task.raw_description.length > 120
            ? task.raw_description.slice(0, 120) + "…"
            : task.raw_description}
        </p>
      )}

      <div className="task-card-footer">
        <span className="task-type-tag">{TYPE_LABELS[task.task_type] || "Other"}</span>
        {dueDate && (
          <span className={`task-due ${isOverdue ? "task-overdue" : ""}`}>
            {isOverdue ? "⚠ " : "📅 "}
            {dueDate}
          </span>
        )}
      </div>
    </button>
  );
}
