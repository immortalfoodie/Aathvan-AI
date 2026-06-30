import { useState, useEffect } from "react";
import client from "../api/client";

export default function TaskAutopsy({ taskId }) {
  const [autopsy, setAutopsy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAutopsy() {
      try {
        const res = await client.get(`/tasks/${taskId}/autopsy`);
        setAutopsy(res.data);
      } catch (err) {
        if (err.response?.status === 404) {
          setError("Not enough data to calculate an autopsy report.");
        } else {
          setError("Failed to load autopsy.");
        }
      } finally {
        setLoading(false);
      }
    }
    fetchAutopsy();
  }, [taskId]);

  if (loading) {
    return <div className="text-neutral-400 text-sm">Loading autopsy data...</div>;
  }

  if (error) {
    return <div className="text-neutral-500 text-sm">{error}</div>;
  }

  if (!autopsy) return null;

  return (
    <div className="task-autopsy p-4 bg-neutral-900 border border-neutral-700 rounded mt-6">
      <h3 className="text-lg font-bold mb-2 text-white">Deadline Autopsy 🔍</h3>
      <p className="text-sm text-neutral-300 mb-4">{autopsy.takeaway}</p>
      
      <div className="mb-4 text-sm text-neutral-400">
        <div><strong>Total Estimated:</strong> {autopsy.total_estimated} hrs</div>
        <div><strong>Total Actual:</strong> {autopsy.total_actual} hrs</div>
      </div>

      <div className="space-y-2">
        {autopsy.steps.map((step, idx) => (
          <div key={idx} className="flex justify-between text-xs border-b border-neutral-800 pb-1">
            <span className="truncate w-1/2" title={step.title}>{step.title}</span>
            <span className="w-1/4 text-right">{step.estimated_hours}h est.</span>
            <span className={`w-1/4 text-right ${step.difference > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {step.actual_hours}h act.
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
