import React, { useRef, useEffect } from 'react';
import { Brain, Zap, Sparkles } from 'lucide-react';

interface VisualizationPanelProps {
  aiState: {
    quantumState: number[];
    chaosState: number[];
    activePerspectives: string[];
    ethicalScore: number;
    processingPower: number;
  };
  darkMode: boolean;
}

const VisualizationPanel: React.FC<VisualizationPanelProps> = ({ 
  aiState,
  darkMode
}) => {
  const quantumCanvasRef = useRef<HTMLCanvasElement>(null);
  const neuralCanvasRef = useRef<HTMLCanvasElement>(null);
  
  // Draw quantum state visualization
  useEffect(() => {
    const canvas = quantumCanvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw quantum state as a particle system
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.8;
    
    // Background circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fillStyle = darkMode ? 'rgba(30, 58, 138, 0.2)' : 'rgba(219, 234, 254, 0.5)';
    ctx.fill();
    
    // Draw quantum particles
    aiState.quantumState.forEach((state, i) => {
      const angle = (i / aiState.quantumState.length) * Math.PI * 2;
      const distance = state * radius;
      const x = centerX + Math.cos(angle) * distance;
      const y = centerY + Math.sin(angle) * distance;
      
      // Particle
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, 15);
      gradient.addColorStop(0, darkMode ? 'rgba(147, 51, 234, 0.9)' : 'rgba(147, 51, 234, 0.7)');
      gradient.addColorStop(1, darkMode ? 'rgba(147, 51, 234, 0)' : 'rgba(147, 51, 234, 0)');
      
      ctx.beginPath();
      ctx.arc(x, y, 15, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      
      // Connection to center
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = darkMode ? 'rgba(147, 51, 234, 0.4)' : 'rgba(147, 51, 234, 0.3)';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
    
    // Draw center node
    ctx.beginPath();
    ctx.arc(centerX, centerY, 8, 0, Math.PI * 2);
    ctx.fillStyle = darkMode ? '#a855f7' : '#8b5cf6';
    ctx.fill();
  }, [aiState.quantumState, darkMode]);
  
  // Draw neural network visualization
  useEffect(() => {
    const canvas = neuralCanvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Define layers
    const layers = [3, 5, 5, 2]; // Input, hidden, hidden, output
    const nodeSize = 6;
    const layerSpacing = canvas.width / (layers.length + 1);
    const neuronColor = darkMode ? '#22c55e' : '#10b981';
    const connectionColor = darkMode ? 'rgba(34, 197, 94, 0.2)' : 'rgba(16, 185, 129, 0.1)';
    const activeConnectionColor = darkMode ? 'rgba(34, 197, 94, 0.6)' : 'rgba(16, 185, 129, 0.5)';
    
    // Draw connections and nodes
    for (let l = 0; l < layers.length - 1; l++) {
      const currentLayerSize = layers[l];
      const nextLayerSize = layers[l + 1];
      const currentX = (l + 1) * layerSpacing;
      const nextX = (l + 2) * layerSpacing;
      
      for (let i = 0; i < currentLayerSize; i++) {
        const currentY = (i + 1) * (canvas.height / (currentLayerSize + 1));
        
        for (let j = 0; j < nextLayerSize; j++) {
          const nextY = (j + 1) * (canvas.height / (nextLayerSize + 1));
          
          // Draw connection
          ctx.beginPath();
          ctx.moveTo(currentX, currentY);
          ctx.lineTo(nextX, nextY);
          
          // Randomly activate some connections based on chaos state
          const isActive = Math.random() < aiState.chaosState[l % aiState.chaosState.length];
          ctx.strokeStyle = isActive ? activeConnectionColor : connectionColor;
          ctx.lineWidth = isActive ? 1.5 : 0.5;
          ctx.stroke();
        }
      }
    }
    
    // Draw nodes
    for (let l = 0; l < layers.length; l++) {
      const layerSize = layers[l];
      const x = (l + 1) * layerSpacing;
      
      for (let i = 0; i < layerSize; i++) {
        const y = (i + 1) * (canvas.height / (layerSize + 1));
        
        // Node
        ctx.beginPath();
        ctx.arc(x, y, nodeSize, 0, Math.PI * 2);
        
        // Node color with pulsing effect based on quantum state
        const stateIndex = (l + i) % aiState.quantumState.length;
        const pulseFactor = 0.7 + (aiState.quantumState[stateIndex] * 0.3);
        
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, nodeSize * 1.5);
        gradient.addColorStop(0, neuronColor);
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');
        
        ctx.fillStyle = gradient;
        ctx.fill();
      }
    }
  }, [aiState.chaosState, aiState.quantumState, darkMode]);
  
  return (
    <div className={`hidden md:flex md:w-1/3 flex-col overflow-hidden border-l ${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
    } transition-colors duration-300`}>
      <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <h2 className="text-lg font-semibold flex items-center">
          <Brain className="mr-2" size={18} />
          Codette State Visualization
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <h3 className="text-md font-semibold mb-2 flex items-center">
            <Sparkles className="mr-2" size={16} />
            Quantum State
          </h3>
          <canvas 
            ref={quantumCanvasRef} 
            width={300} 
            height={200} 
            className="w-full rounded-md"
          />
          <div className="grid grid-cols-3 gap-2 mt-3">
            {aiState.quantumState.map((value, index) => (
              <div key={`quantum-${index}`} className="text-center">
                <div className={`text-xs uppercase font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Q{index + 1}
                </div>
                <div className="text-lg font-mono">{value.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
        
        <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <h3 className="text-md font-semibold mb-2 flex items-center">
            <Brain className="mr-2" size={16} />
            Neural Activity
          </h3>
          <canvas 
            ref={neuralCanvasRef} 
            width={300} 
            height={200} 
            className="w-full rounded-md"
          />
          <div className="grid grid-cols-4 gap-2 mt-3">
            {aiState.chaosState.map((value, index) => (
              <div key={`chaos-${index}`} className="text-center">
                <div className={`text-xs uppercase font-semibold ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  C{index + 1}
                </div>
                <div className="text-lg font-mono">{value.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
        
        <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <h3 className="text-md font-semibold mb-3 flex items-center">
            <Zap className="mr-2" size={16} />
            Active Perspectives
          </h3>
          <div className="flex flex-wrap gap-2">
            {aiState.activePerspectives.map((perspective, index) => (
              <div 
                key={perspective} 
                className={`px-3 py-1 rounded-full text-sm ${
                  darkMode 
                    ? 'bg-indigo-900 text-indigo-200' 
                    : 'bg-indigo-100 text-indigo-800'
                }`}
              >
                {perspective.replace('_', ' ')}
              </div>
            ))}
          </div>
        </div>
        
        <div className={`rounded-lg p-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <h3 className="text-md font-semibold mb-3">Performance Metrics</h3>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm">Ethical Governance</span>
                <span className="text-sm font-semibold">{Number(aiState.ethicalScore) * 100}%</span>
              </div>
              <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}>
                <div 
                  className="h-full rounded-full bg-green-500"
                  style={{ width: `${Number(aiState.ethicalScore) * 100}%` }}
                ></div>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm">Processing Power</span>
                <span className="text-sm font-semibold">{Number(aiState.processingPower) * 100}%</span>
              </div>
              <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}>
                <div 
                  className="h-full rounded-full bg-blue-500"
                  style={{ width: `${Number(aiState.processingPower) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VisualizationPanel;