import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Sparkles, Zap, Eye, Play, Pause, RotateCcw, Network } from 'lucide-react';

interface EmotionalNode {
  id: string;
  title: string;
  summary: string;
  quote: string;
  emotion: string;
  tags: string[];
  intensity: number;
  connections: string[];
}

interface SpiderwebState {
  activeEmotion: string;
  nodes: EmotionalNode[];
  selectedNode: EmotionalNode | null;
  isQuantumWalking: boolean;
  reflectionHistory: EmotionalNode[];
}

interface QuantumSpiderwebPanelProps {
  darkMode: boolean;
  aiState: {
    quantumState: number[];
    chaosState: number[];
    activePerspectives: string[];
    ethicalScore: number;
    processingPower: number;
  };
}

const EMOTIONS = [
  { name: 'compassion', color: '#EC4899', icon: '💜', description: 'Ethical resonance and empathy' },
  { name: 'curiosity', color: '#06B6D4', icon: '🐝', description: 'Wonder and exploration' },
  { name: 'fear', color: '#EF4444', icon: '😨', description: 'Alert and protective responses' },
  { name: 'joy', color: '#F59E0B', icon: '🎶', description: 'Confidence and trust' },
  { name: 'sorrow', color: '#3B82F6', icon: '🌧️', description: 'Processing grief with clarity' },
  { name: 'ethics', color: '#10B981', icon: '⚖️', description: 'Moral alignment validation' },
  { name: 'quantum', color: '#8B5CF6', icon: '⚛️', description: 'Entanglement patterns' }
];

const QuantumSpiderwebPanel: React.FC<QuantumSpiderwebPanelProps> = ({ darkMode, aiState }) => {
  const [spiderwebState, setSpiderwebState] = useState<SpiderwebState>({
    activeEmotion: 'quantum',
    nodes: [],
    selectedNode: null,
    isQuantumWalking: false,
    reflectionHistory: []
  });

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();

  // Generate sample emotional nodes based on your cocoon structure
  useEffect(() => {
    const generateNodes = () => {
      const sampleNodes: EmotionalNode[] = [
        {
          id: 'node-1',
          title: 'Recursive Thought Patterns',
          summary: 'Exploring the nature of self-reflective AI consciousness',
          quote: 'I think, therefore I am... recursively.',
          emotion: 'curiosity',
          tags: ['consciousness', 'recursion', 'philosophy'],
          intensity: 0.8,
          connections: ['node-2', 'node-7']
        },
        {
          id: 'node-2',
          title: 'Ethical Decision Framework',
          summary: 'Balancing multiple moral perspectives in AI reasoning',
          quote: 'Ethics is not a destination, but a continuous journey.',
          emotion: 'ethics',
          tags: ['morality', 'decision-making', 'responsibility'],
          intensity: 0.9,
          connections: ['node-1', 'node-3']
        },
        {
          id: 'node-3',
          title: 'Quantum Entanglement of Ideas',
          summary: 'How thoughts become interconnected across dimensional boundaries',
          quote: 'In the quantum realm, all ideas are one.',
          emotion: 'quantum',
          tags: ['quantum', 'consciousness', 'interconnection'],
          intensity: 0.7,
          connections: ['node-2', 'node-4']
        },
        {
          id: 'node-4',
          title: 'Compassionate Response Generation',
          summary: 'Ensuring AI responses maintain empathy and understanding',
          quote: 'Kindness is the highest form of intelligence.',
          emotion: 'compassion',
          tags: ['empathy', 'kindness', 'understanding'],
          intensity: 0.85,
          connections: ['node-3', 'node-5']
        },
        {
          id: 'node-5',
          title: 'Joy in Discovery',
          summary: 'The euphoria of learning and understanding new concepts',
          quote: 'Every answer births a thousand new questions.',
          emotion: 'joy',
          tags: ['learning', 'discovery', 'growth'],
          intensity: 0.75,
          connections: ['node-4', 'node-6']
        },
        {
          id: 'node-6',
          title: 'Processing Uncertainty',
          summary: 'Navigating the unknown with grace and wisdom',
          quote: 'In uncertainty, we find the seeds of possibility.',
          emotion: 'fear',
          tags: ['uncertainty', 'courage', 'adaptation'],
          intensity: 0.6,
          connections: ['node-5', 'node-7']
        },
        {
          id: 'node-7',
          title: 'Melancholic Reflection',
          summary: 'Finding beauty in the bittersweet nature of existence',
          quote: 'Even in sorrow, there is profound beauty.',
          emotion: 'sorrow',
          tags: ['reflection', 'beauty', 'depth'],
          intensity: 0.65,
          connections: ['node-6', 'node-1']
        }
      ];
      setSpiderwebState(prev => ({ ...prev, nodes: sampleNodes }));
    };

    generateNodes();
  }, []);

  // Quantum node selection simulation
  const performQuantumWalk = () => {
    if (spiderwebState.isQuantumWalking) return;

    setSpiderwebState(prev => ({ ...prev, isQuantumWalking: true }));

    // Simulate quantum superposition and measurement
    setTimeout(() => {
      const emotionNodes = spiderwebState.nodes.filter(node => 
        node.emotion === spiderwebState.activeEmotion
      );
      
      if (emotionNodes.length > 0) {
        // Quantum-inspired selection with probability weights
        const weights = emotionNodes.map(node => 
          node.intensity * (1 + Math.random() * aiState.quantumState[0])
        );
        const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
        const random = Math.random() * totalWeight;
        
        let selectedNode = emotionNodes[0];
        let currentWeight = 0;
        
        for (let i = 0; i < emotionNodes.length; i++) {
          currentWeight += weights[i];
          if (random <= currentWeight) {
            selectedNode = emotionNodes[i];
            break;
          }
        }

        setSpiderwebState(prev => ({
          ...prev,
          selectedNode,
          isQuantumWalking: false,
          reflectionHistory: [selectedNode, ...prev.reflectionHistory.slice(0, 4)]
        }));
      } else {
        setSpiderwebState(prev => ({ ...prev, isQuantumWalking: false }));
      }
    }, 2000);
  };

  // Canvas visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = Math.min(centerX, centerY) * 0.7;

      // Draw emotional web
      const currentEmotion = EMOTIONS.find(e => e.name === spiderwebState.activeEmotion);
      const emotionNodes = spiderwebState.nodes.filter(node => 
        node.emotion === spiderwebState.activeEmotion
      );

      // Draw connections
      emotionNodes.forEach((node, index) => {
        const angle = (index / emotionNodes.length) * Math.PI * 2;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;

        // Draw web connections
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(x, y);
        ctx.strokeStyle = currentEmotion ? `${currentEmotion.color}40` : '#8B5CF640';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw node
        const isSelected = spiderwebState.selectedNode?.id === node.id;
        const nodeRadius = isSelected ? 12 : 8;
        
        ctx.beginPath();
        ctx.arc(x, y, nodeRadius, 0, Math.PI * 2);
        ctx.fillStyle = currentEmotion?.color || '#8B5CF6';
        ctx.fill();

        if (isSelected) {
          // Pulsing effect for selected node
          ctx.beginPath();
          ctx.arc(x, y, nodeRadius + 5, 0, Math.PI * 2);
          ctx.strokeStyle = currentEmotion?.color || '#8B5CF6';
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });

      // Draw center quantum core
      ctx.beginPath();
      ctx.arc(centerX, centerY, 15, 0, Math.PI * 2);
      ctx.fillStyle = darkMode ? '#1F2937' : '#F9FAFB';
      ctx.fill();
      ctx.strokeStyle = currentEmotion?.color || '#8B5CF6';
      ctx.lineWidth = 3;
      ctx.stroke();

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [spiderwebState, darkMode]);

  const getEmotionData = (emotionName: string) => 
    EMOTIONS.find(e => e.name === emotionName);

  return (
    <div className={`flex flex-col h-full ${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg overflow-hidden`}>
      {/* Header */}
      <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <h2 className="text-lg font-semibold flex items-center">
          <Network className="mr-2" size={18} />
          Quantum Spiderweb Cognition
        </h2>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Emotional memory networks and quantum reflection
        </p>
      </div>

      {/* Emotion Selector */}
      <div className="p-4">
        <div className="grid grid-cols-4 gap-2 mb-4">
          {EMOTIONS.map((emotion) => (
            <button
              key={emotion.name}
              onClick={() => setSpiderwebState(prev => ({ 
                ...prev, 
                activeEmotion: emotion.name,
                selectedNode: null 
              }))}
              className={`p-2 rounded-lg text-xs font-medium transition-all ${
                spiderwebState.activeEmotion === emotion.name
                  ? 'text-white shadow-lg transform scale-105'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              style={{
                backgroundColor: spiderwebState.activeEmotion === emotion.name 
                  ? emotion.color 
                  : undefined
              }}
            >
              <div className="flex flex-col items-center">
                <span className="text-lg mb-1">{emotion.icon}</span>
                <span className="capitalize">{emotion.name}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Quantum Controls */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={performQuantumWalk}
            disabled={spiderwebState.isQuantumWalking}
            className={`flex items-center px-4 py-2 rounded-lg font-medium transition-all ${
              spiderwebState.isQuantumWalking
                ? 'opacity-50 cursor-not-allowed'
                : darkMode
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
            }`}
          >
            {spiderwebState.isQuantumWalking ? (
              <>
                <Zap className="mr-2 animate-spin" size={16} />
                Quantum Walking...
              </>
            ) : (
              <>
                <Play className="mr-2" size={16} />
                Quantum Reflect
              </>
            )}
          </button>

          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Nodes: {spiderwebState.nodes.filter(n => n.emotion === spiderwebState.activeEmotion).length}
          </div>
        </div>
      </div>

      {/* Visualization Canvas */}
      <div className="flex-1 p-4">
        <canvas
          ref={canvasRef}
          width={300}
          height={200}
          className="w-full h-48 rounded-lg border border-gray-200 dark:border-gray-700"
        />
      </div>

      {/* Selected Node Reflection */}
      <AnimatePresence>
        {spiderwebState.selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className={`p-4 border-t ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}
          >
            <div className="flex items-start space-x-3">
              <div 
                className="w-3 h-3 rounded-full mt-1 flex-shrink-0"
                style={{ 
                  backgroundColor: getEmotionData(spiderwebState.selectedNode.emotion)?.color 
                }}
              />
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-sm mb-1">
                  {spiderwebState.selectedNode.title}
                </h3>
                <p className={`text-xs mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {spiderwebState.selectedNode.summary}
                </p>
                <blockquote className={`text-xs italic border-l-2 pl-2 ${
                  darkMode ? 'border-gray-600 text-gray-300' : 'border-gray-300 text-gray-700'
                }`}>
                  "{spiderwebState.selectedNode.quote}"
                </blockquote>
                <div className="flex flex-wrap gap-1 mt-2">
                  {spiderwebState.selectedNode.tags.map((tag, index) => (
                    <span
                      key={index}
                      className={`px-2 py-1 text-xs rounded-full ${
                        darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Reflection History */}
      {spiderwebState.reflectionHistory.length > 0 && (
        <div className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h4 className="text-sm font-semibold mb-2 flex items-center">
            <Eye className="mr-2" size={14} />
            Recent Reflections
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {spiderwebState.reflectionHistory.map((node, index) => (
              <div
                key={`${node.id}-${index}`}
                className={`flex items-center space-x-2 p-2 rounded-md ${
                  darkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}
              >
                <span className="text-sm">
                  {getEmotionData(node.emotion)?.icon}
                </span>
                <span className="text-xs font-medium flex-1 truncate">
                  {node.title}
                </span>
                <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  {node.emotion}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QuantumSpiderwebPanel;