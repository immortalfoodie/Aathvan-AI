import { useState, useEffect } from "react";
import client from "../api/client";

export default function MomentumWidget() {
  const [momentum, setMomentum] = useState(null);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    async function fetchEngagement() {
      try {
        // Quietly update streak on load
        const streakRes = await client.post('/engagement/momentum/streak');
        setStreak(streakRes.data.streak);

        const momentumRes = await client.get('/engagement/momentum/today');
        setMomentum(momentumRes.data);
      } catch (err) {
        console.error("Failed to load engagement data:", err);
      }
    }
    fetchEngagement();
  }, []);

  if (!momentum) return null;

  return (
    <div className="flex gap-4 mb-6">
      <div className="flex-1 bg-neutral-900 border border-neutral-700 p-4 rounded shadow-sm flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-neutral-300 uppercase tracking-wider">Momentum</h3>
          <p className="text-neutral-400 mt-1 text-sm">{momentum.message}</p>
        </div>
        {momentum.has_data && (
          <div className="text-2xl font-bold text-indigo-400">
            {momentum.percentage}%
          </div>
        )}
      </div>

      <div className="bg-neutral-900 border border-neutral-700 p-4 rounded shadow-sm flex items-center justify-center min-w-[120px]">
        <div className="text-center">
          <div className="text-2xl mb-1">🔥</div>
          <div className="text-sm font-semibold text-neutral-300">
            {streak} {streak === 1 ? 'day' : 'days'}
          </div>
        </div>
      </div>
    </div>
  );
}
