import React from 'react';
import { Menu, Moon, Sun, ChevronRight, Brain, Zap } from 'lucide-react';

interface HeaderProps {
  toggleSidebar: () => void;
  toggleDarkMode: () => void;
  darkMode: boolean;
  aiState: {
    quantumState: number[];
    chaosState: number[];
    activePerspectives: string[];
    ethicalScore: number;
    processingPower: number;
  };
}

const Header: React.FC<HeaderProps> = ({
  toggleSidebar,
  toggleDarkMode,
  darkMode,
  aiState
}) => {
  return (
    <header className={`h-16 flex items-center justify-between px-4 border-b transition-colors duration-300 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="flex items-center">
        <button
          onClick={toggleSidebar}
          className={`p-2 rounded-md ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
        >
          <Menu size={20} />
        </button>
        
        <div className="ml-4 flex items-center">
          <Brain className="text-purple-600" size={24} />
          <h1 className="ml-2 text-xl font-bold">Codette AI</h1>
          <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${darkMode ? 'bg-purple-900 text-purple-200' : 'bg-purple-100 text-purple-800'}`}>
            v2.0
          </span>
        </div>
      </div>
      
      <div className="flex items-center space-x-4">
        <div className={`hidden md:flex items-center py-1 px-3 rounded-full text-sm ${
          darkMode ? 'bg-blue-900 text-blue-200' : 'bg-blue-100 text-blue-800'
        }`}>
          <Zap size={14} className="mr-1" />
          <span className="font-medium">Quantum State:</span>
          <span className="ml-1 font-mono">
            [{aiState.quantumState.map(v => v.toFixed(1)).join(', ')}]
          </span>
        </div>
        
        <button
          onClick={toggleDarkMode}
          className={`p-2 rounded-md ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
        >
          {darkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>
    </header>
  );
};

export default Header;