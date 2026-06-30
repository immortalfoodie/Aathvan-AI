/**
 * Simple hook for managing async API call state.
 */
import { useState, useCallback } from "react";

export function useApi(apiFunction) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiFunction(...args);
        setData(result);
        return result;
      } catch (err) {
        const message =
          err.response?.data?.detail || err.message || "Something went wrong";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [apiFunction]
  );

  return { data, error, loading, execute };
}
