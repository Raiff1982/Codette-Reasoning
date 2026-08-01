export const getPerspectiveColor = (perspective: string): string => {
  const colors: Record<string, string> = {
    newton: '#3B82F6',
    davinci: '#8B5CF6',
    neural_network: '#10B981',
    philosophical: '#F59E0B',
    quantum_computing: '#EC4899',
    bias_mitigation: '#6366F1',
    creative: '#F97316',
    resilient_kindness: '#14B8A6'
  };

  return colors[perspective.toLowerCase()] || '#6B7280';
};