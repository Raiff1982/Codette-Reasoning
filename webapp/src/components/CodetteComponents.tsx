import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Sparkles, Zap } from 'lucide-react';

export function PerspectiveTrail({ perspectives }: { perspectives: string[] }) {
  const [selectedPerspective, setSelectedPerspective] = useState<string | null>(null);
  
  const getDescription = (perspective: string) => {
    const descriptions: Record<string, string> = {
      newton: "Applies logical, systematic reasoning to analyze problems",
      davinci: "Explores creative and innovative solutions through artistic thinking",
      neural_network: "Processes information through parallel distributed cognition",
      philosophical: "Examines deep implications and fundamental principles",
      quantum_computing: "Explores multiple solution paths simultaneously",
      bias_mitigation: "Ensures balanced and fair consideration of all aspects",
      creative: "Generates novel and imaginative approaches",
      resilient_kindness: "Maintains empathetic and constructive dialogue"
    };
    return descriptions[perspective.toLowerCase()] || "A unique perspective on problem-solving";
  };

  const getIcon = (perspective: string) => {
    switch (perspective.toLowerCase()) {
      case 'newton':
        return <Brain className="w-4 h-4" />;
      case 'davinci':
        return <Sparkles className="w-4 h-4" />;
      default:
        return <Zap className="w-4 h-4" />;
    }
  };

  return (
    <div className="mt-4 space-y-2">
      <p className="text-sm font-semibold text-purple-700 dark:text-purple-400">
        Active Perspectives:
      </p>
      <div className="space-y-2">
        <AnimatePresence>
          {perspectives.map((perspective, index) => (
            <motion.div
              key={perspective}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ delay: index * 0.1 }}
              className="relative"
            >
              <motion.button
                onClick={() => setSelectedPerspective(
                  selectedPerspective === perspective ? null : perspective
                )}
                className={`w-full flex items-center px-3 py-2 rounded-lg transition-colors ${
                  selectedPerspective === perspective
                    ? 'bg-purple-100 dark:bg-purple-900'
                    : 'hover:bg-purple-50 dark:hover:bg-purple-900/50'
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <span className={`flex items-center text-sm ${
                  selectedPerspective === perspective
                    ? 'text-purple-700 dark:text-purple-300'
                    : 'text-purple-600 dark:text-purple-400'
                }`}>
                  {getIcon(perspective)}
                  <span className="ml-2 capitalize">
                    {perspective.replace(/_/g, ' ')}
                  </span>
                </span>
              </motion.button>
              
              <AnimatePresence>
                {selectedPerspective === perspective && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 ml-8 p-3 rounded-lg bg-purple-50 dark:bg-purple-900/30"
                  >
                    <p className="text-sm text-purple-700 dark:text-purple-300">
                      {getDescription(perspective)}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function CocoonReplay({ cocoons }: { cocoons: string[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const timer = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % cocoons.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [paused, cocoons.length]);

  return (
    <div className="mt-4 text-sm text-green-700 dark:text-green-400">
      <p className="font-semibold">Cocoon Memory:</p>
      <motion.div 
        className="bg-green-100 dark:bg-green-900/30 p-2 rounded-md max-h-40 overflow-y-scroll"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {cocoons.map((cocoon, idx) => (
          <motion.pre 
            key={idx} 
            className={`whitespace-pre-wrap text-xs mb-2 transition-colors duration-300 ${
              idx === activeIndex ? 'bg-green-200 dark:bg-green-800 rounded p-1' : ''
            }`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: idx * 0.1 }}
          >
            {cocoon}
          </motion.pre>
        ))}
      </motion.div>
    </div>
  );
}

export function CollapseDetector({ isUnstable }: { isUnstable: boolean }) {
  return (
    <motion.div
      animate={{
        scale: isUnstable ? [1, 1.3, 1] : 1,
        opacity: isUnstable ? [0.6, 1, 0.6] : 1,
        boxShadow: isUnstable ? "0 0 0 6px rgba(255,0,0,0.5)" : "none"
      }}
      transition={{ duration: 1.5, repeat: Infinity }}
      className={`w-4 h-4 rounded-full mt-2 ml-2 ${
        isUnstable ? "bg-red-500" : "bg-blue-300"
      }`}
      title={isUnstable ? "Quantum Instability Detected" : "Stable"}
    />
  );
}

export interface CodetteResponse {
  text: string;
  instabilityFlag: boolean;
  perspectivesUsed: string[];
  cocoonLog: string[];
  forceRefresh: (reason?: string) => void;
}

export function CodetteResponseCard({ response }: { response: CodetteResponse }) {
  const [loopCount, setLoopCount] = useState(0);
  const [introspectiveMessage, setIntrospectiveMessage] = useState<string | null>(null);

  useEffect(() => {
    const history = JSON.parse(localStorage.getItem("codette_recent") || "[]");

    const isRepeat = history.includes(response.text);
    if (isRepeat) {
      console.warn("Codette is repeating again.");
      setLoopCount(prev => prev + 1);
      setIntrospectiveMessage("I sense I've looped. Let me try a new direction.");
      if (response.forceRefresh) response.forceRefresh(`diverge-${Date.now()}`);
    } else {
      setLoopCount(0);
      setIntrospectiveMessage(null);
    }

    // Keep recent 5 responses
    const newHistory = [...history, response.text].slice(-5);
    localStorage.setItem("codette_recent", JSON.stringify(newHistory));
  }, [response.text]);

  return (
    <motion.div 
      className="border border-gray-200 dark:border-gray-700 p-4 rounded-xl shadow-sm bg-white dark:bg-gray-800 max-w-[80%]"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <p className="whitespace-pre-wrap text-sm dark:text-gray-200">{response.text}</p>
      {introspectiveMessage && (
        <motion.p 
          className="text-xs text-rose-600 dark:text-rose-400 italic mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {introspectiveMessage}
        </motion.p>
      )}
      {loopCount > 0 && (
        <p className="text-xs text-orange-600 dark:text-orange-400 mt-1">
          Recursion count: {loopCount}
        </p>
      )}
      {loopCount > 2 && (
        <button 
          onClick={() => response.forceRefresh()}
          className="mt-2 px-2 py-1 text-xs bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 dark:text-red-200 rounded"
        >
          Force New Thought
        </button>
      )}
      <div className="flex items-center mt-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">System Readout:</span>
        <CollapseDetector isUnstable={response.instabilityFlag || loopCount > 2} />
      </div>
      <PerspectiveTrail perspectives={response.perspectivesUsed} />
      <CocoonReplay cocoons={response.cocoonLog} />
    </motion.div>
  );
}