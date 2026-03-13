import { useState } from 'react';
import { startCommitment, completeCommitment } from '../api/digiwell';

export function useCommitment() {
  const [activeCommitment, setActiveCommitment] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const startNewCommitment = async (details) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await startCommitment(details);
      setActiveCommitment(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const markComplete = async (id) => {
    setIsLoading(true);
    try {
      await completeCommitment(id);
      setActiveCommitment(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return { activeCommitment, startNewCommitment, markComplete, isLoading, error };
}
