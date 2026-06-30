/**
 * Dashboard page — three-section layout:
 * 1. "Today" priority list (what to work on next)
 * 2. "At a Glance" overview widget
 * 3. "My Tasks" grid (existing task cards)
 */
import { useState, useEffect, useCallback } from "react";
import client from "../api/client";
import TaskCard from "../components/TaskCard";
import NewTaskModal from "../components/NewTaskModal";
import TodayPriorityList from "../components/TodayPriorityList";
import OverviewWidget from "../components/OverviewWidget";

export default function DashboardPage() {
  const [tasks, setTasks] = useState([]);
  const [priorities, setPriorities] = useState([]);
  const [overview, setOverview] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [tasksRes, priorityRes, overviewRes] = await Promise.all([
        client.get("/tasks"),
        client.get("/priority/today").catch(() => ({ data: [] })),
        client.get("/priority/overview").catch(() => ({ data: [] })),
      ]);
      setTasks(tasksRes.data);
      setPriorities(priorityRes.data);
      setOverview(overviewRes.data);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleCreateTask = async (payload) => {
    await client.post("/tasks", payload);
    await fetchAll();
  };

  const hasPriorities = priorities.length > 0;
  const hasOverview = overview.length > 0;

  return (
    <div className="dashboard" id="dashboard-page">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <button
          className="btn btn-primary"
          onClick={() => setShowModal(true)}
          id="new-task-btn"
        >
          + New Task
        </button>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="loading-spinner" />
        </div>
      ) : (
        <div className="dashboard-sections">
          {/* Section 1: Today's Priorities */}
          {hasPriorities && (
            <section className="today-section" id="today-section">
              <h2 className="section-title">🎯 Today — What to Work on Next</h2>
              <TodayPriorityList items={priorities} onUpdate={fetchAll} />
            </section>
          )}

          {/* Section 2: At a Glance */}
          {hasOverview && (
            <section className="overview-section">
              <OverviewWidget items={overview} />
            </section>
          )}

          {/* Section 3: All Tasks */}
          <section className="tasks-section">
            <h2 className="section-title" style={{ marginBottom: "16px" }}>📋 My Tasks</h2>
            {tasks.length === 0 ? (
              <div className="empty-state" id="empty-tasks">
                <div className="empty-icon">📋</div>
                <h2>No tasks yet</h2>
                <p>Create your first task to get started!</p>
                <button
                  className="btn btn-primary"
                  onClick={() => setShowModal(true)}
                >
                  + Create a Task
                </button>
              </div>
            ) : (
              <div className="task-grid">
                {tasks.map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {showModal && (
        <NewTaskModal
          onClose={() => setShowModal(false)}
          onSubmit={handleCreateTask}
        />
      )}
    </div>
  );
}
