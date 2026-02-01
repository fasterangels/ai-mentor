import { useState, useEffect } from 'react';
import { apiClient } from '@/services/api';

export function useOllama() {
  const [isConnected, setIsConnected] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  const checkStatus = async () => {
    try {
      const health = await apiClient.checkHealth();
      setIsConnected(health.ollama_connected);
    } catch (error) {
      setIsConnected(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, []);

  return { isConnected, isChecking, refresh: checkStatus };
}