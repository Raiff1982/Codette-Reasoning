import { createContext, useContext } from 'react';

interface CodetteContextType {
  recursionCount: number;
  activePerspectives: string[];
  cocoonTrace: string[];
  lastStableTimestamp: number;
  fallbackState: boolean;
  resetFallback: () => void;
}

export const CodetteContext = createContext<CodetteContextType>({
  recursionCount: 0,
  activePerspectives: [],
  cocoonTrace: [],
  lastStableTimestamp: Date.now(),
  fallbackState: false,
  resetFallback: () => {},
});

export const useCodetteContext = () => {
  const context = useContext(CodetteContext);
  if (!context) {
    throw new Error('useCodetteContext must be used within a CodetteProvider');
  }
  return context;
};