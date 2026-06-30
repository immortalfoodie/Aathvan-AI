import { useState } from "react";
import client from "../api/client";

export default function InactionSimulationModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [simulation, setSimulation] = useState(null);

  const fetchSimulation = async () => {
    setLoading(true);
    try {
      const res = await client.get('/engagement/simulate/inaction');
      setSimulation(res.data);
    } catch (err) {
      console.error("Failed to load simulation:", err);
      alert("Failed to load simulation");
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    setIsOpen(true);
    fetchSimulation();
  };

  if (!isOpen) {
    return (
      <button 
        onClick={handleOpen}
        className="text-xs text-neutral-400 hover:text-white underline mt-4"
      >
        What if I do nothing today?
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-neutral-900 border border-neutral-700 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 relative">
        <button 
          onClick={() => setIsOpen(false)}
          className="absolute top-4 right-4 text-neutral-400 hover:text-white text-xl"
        >
          &times;
        </button>

        <h2 className="text-2xl font-bold mb-6 text-white border-b border-neutral-800 pb-2">
          The Cost of Inaction
        </h2>

        {loading ? (
          <div className="text-center py-10 text-neutral-400">Simulating alternate timeline...</div>
        ) : simulation ? (
          <div className="space-y-6">
            <p className="text-neutral-300">
              You have <strong className="text-white">{simulation.active_tasks_count} active tasks</strong> with a total of <strong className="text-white">{simulation.total_remaining_hours.toFixed(1)} hours</strong> of work remaining.
              Here's what happens if you make zero progress today and shift everything to tomorrow.
            </p>

            {/* Missed Deadlines */}
            <div className="bg-red-950/30 border border-red-900 p-4 rounded">
              <h3 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                ⚠️ Missed Deadlines
              </h3>
              {simulation.missed_deadlines.length > 0 ? (
                <ul className="list-disc pl-5 space-y-1 text-sm text-red-200">
                  {simulation.missed_deadlines.map(md => (
                    <li key={md.task_id}>
                      <strong>{md.task_title}</strong> would miss its deadline ({md.due_date}) by {md.missed_by_days} day(s).
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-neutral-300">You wouldn't miss any final deadlines, but your schedule gets tighter.</p>
              )}
            </div>

            {/* Timeline Comparison */}
            <div>
              <h3 className="font-bold text-white mb-3">Timeline Comparison (Next 7 Days)</h3>
              <div className="grid grid-cols-2 gap-4">
                
                {/* Current Plan */}
                <div className="bg-neutral-800 p-3 rounded border border-neutral-700">
                  <h4 className="text-sm font-semibold text-neutral-400 mb-2 border-b border-neutral-700 pb-1">Current Plan</h4>
                  <div className="space-y-2">
                    {simulation.current_timeline.map(day => (
                      <div key={day.date} className="flex items-center text-xs">
                        <span className="w-20 text-neutral-500">{new Date(day.date).toLocaleDateString('en-US', {weekday: 'short', month: 'numeric', day: 'numeric'})}</span>
                        <div className="flex-1 bg-neutral-900 h-4 rounded overflow-hidden">
                          <div 
                            className={`h-full ${day.hours > 6 ? 'bg-red-500' : 'bg-indigo-500'}`} 
                            style={{ width: `${Math.min((day.hours / 10) * 100, 100)}%` }}
                          />
                        </div>
                        <span className="w-10 text-right text-neutral-400 ml-2">{day.hours.toFixed(1)}h</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Inaction Plan */}
                <div className="bg-neutral-800 p-3 rounded border border-neutral-700">
                  <h4 className="text-sm font-semibold text-neutral-400 mb-2 border-b border-neutral-700 pb-1">If You Do Nothing</h4>
                  <div className="space-y-2">
                    {simulation.inaction_timeline.map(day => (
                      <div key={day.date} className="flex items-center text-xs">
                        <span className="w-20 text-neutral-500">{new Date(day.date).toLocaleDateString('en-US', {weekday: 'short', month: 'numeric', day: 'numeric'})}</span>
                        <div className="flex-1 bg-neutral-900 h-4 rounded overflow-hidden">
                          <div 
                            className={`h-full ${day.hours > 6 ? 'bg-red-500' : 'bg-orange-500'}`} 
                            style={{ width: `${Math.min((day.hours / 10) * 100, 100)}%` }}
                          />
                        </div>
                        <span className="w-10 text-right text-neutral-400 ml-2">{day.hours.toFixed(1)}h</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
              <p className="text-xs text-neutral-500 mt-2 text-center">
                (Bars turn red if scheduled hours exceed 6 hours in a single day)
              </p>
            </div>
            
            <div className="flex justify-center mt-6">
              <button 
                onClick={() => setIsOpen(false)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded font-medium"
              >
                Let's get to work instead
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
