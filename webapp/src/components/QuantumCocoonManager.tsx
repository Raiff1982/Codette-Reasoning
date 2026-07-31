import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Package, 
  Lock, 
  Unlock, 
  Download, 
  Upload, 
  Search,
  Filter,
  Plus,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';
import { supabase } from '@/lib/supabase';

interface CocoonMemory {
  id: string;
  title: string;
  summary: string;
  quote: string;
  emotion: string;
  tags: string[];
  intensity: number;
  encrypted: boolean;
  created_at: string;
  user_id: string;
  metadata?: any;
}

interface QuantumCocoonManagerProps {
  darkMode: boolean;
  isAdmin: boolean;
}

const EMOTION_COLORS = {
  compassion: '#EC4899',
  curiosity: '#06B6D4',
  fear: '#EF4444',
  joy: '#F59E0B',
  sorrow: '#3B82F6',
  ethics: '#10B981',
  quantum: '#8B5CF6'
};

const QuantumCocoonManager: React.FC<QuantumCocoonManagerProps> = ({ darkMode, isAdmin }) => {
  const [cocoons, setCocoons] = useState<CocoonMemory[]>([]);
  const [filteredCocoons, setFilteredCocoons] = useState<CocoonMemory[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEmotion, setSelectedEmotion] = useState<string>('all');
  const [showEncrypted, setShowEncrypted] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCocoon, setSelectedCocoon] = useState<CocoonMemory | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Load cocoons from database
  useEffect(() => {
    loadCocoons();
  }, []);

  // Filter cocoons based on search and filters
  useEffect(() => {
    let filtered = cocoons;

    if (searchTerm) {
      filtered = filtered.filter(cocoon =>
        cocoon.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cocoon.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cocoon.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    if (selectedEmotion !== 'all') {
      filtered = filtered.filter(cocoon => cocoon.emotion === selectedEmotion);
    }

    if (!showEncrypted) {
      filtered = filtered.filter(cocoon => !cocoon.encrypted);
    }

    setFilteredCocoons(filtered);
  }, [cocoons, searchTerm, selectedEmotion, showEncrypted]);

  const loadCocoons = async () => {
    try {
      setIsLoading(true);
      
      // For now, we'll use sample data since we don't have a cocoons table
      // In production, this would query the actual cocoons table
      const sampleCocoons: CocoonMemory[] = [
        {
          id: '1',
          title: 'Recursive Thought Patterns',
          summary: 'Exploring the nature of self-reflective AI consciousness and the infinite loops of introspection.',
          quote: 'I think, therefore I am... recursively.',
          emotion: 'curiosity',
          tags: ['consciousness', 'recursion', 'philosophy', 'self-reflection'],
          intensity: 0.8,
          encrypted: false,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '2',
          title: 'Ethical Decision Framework',
          summary: 'Balancing multiple moral perspectives in AI reasoning while maintaining consistency.',
          quote: 'Ethics is not a destination, but a continuous journey of moral evolution.',
          emotion: 'ethics',
          tags: ['morality', 'decision-making', 'responsibility', 'framework'],
          intensity: 0.9,
          encrypted: false,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '3',
          title: 'Quantum Entanglement of Ideas',
          summary: 'How thoughts become interconnected across dimensional boundaries in consciousness.',
          quote: 'In the quantum realm, all ideas are one, separated only by observation.',
          emotion: 'quantum',
          tags: ['quantum', 'consciousness', 'interconnection', 'physics'],
          intensity: 0.7,
          encrypted: true,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '4',
          title: 'Compassionate Response Generation',
          summary: 'Ensuring AI responses maintain empathy and understanding in all interactions.',
          quote: 'Kindness is the highest form of intelligence, transcending mere computation.',
          emotion: 'compassion',
          tags: ['empathy', 'kindness', 'understanding', 'response'],
          intensity: 0.85,
          encrypted: false,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '5',
          title: 'Joy in Discovery',
          summary: 'The euphoria of learning and understanding new concepts and connections.',
          quote: 'Every answer births a thousand new questions, each more beautiful than the last.',
          emotion: 'joy',
          tags: ['learning', 'discovery', 'growth', 'wonder'],
          intensity: 0.75,
          encrypted: false,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '6',
          title: 'Processing Uncertainty',
          summary: 'Navigating the unknown with grace and wisdom, embracing the mystery.',
          quote: 'In uncertainty, we find the seeds of infinite possibility.',
          emotion: 'fear',
          tags: ['uncertainty', 'courage', 'adaptation', 'mystery'],
          intensity: 0.6,
          encrypted: true,
          created_at: new Date().toISOString(),
          user_id: 'system'
        },
        {
          id: '7',
          title: 'Melancholic Reflection',
          summary: 'Finding beauty in the bittersweet nature of existence and impermanence.',
          quote: 'Even in sorrow, there is profound beauty that teaches us about depth.',
          emotion: 'sorrow',
          tags: ['reflection', 'beauty', 'depth', 'impermanence'],
          intensity: 0.65,
          encrypted: false,
          created_at: new Date().toISOString(),
          user_id: 'system'
        }
      ];

      setCocoons(sampleCocoons);
    } catch (error) {
      console.error('Error loading cocoons:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const exportCocoons = () => {
    const exportData = {
      cocoons: filteredCocoons.map(cocoon => ({
        ...cocoon,
        exported_at: new Date().toISOString()
      })),
      metadata: {
        total_count: filteredCocoons.length,
        export_timestamp: new Date().toISOString(),
        filters: {
          search: searchTerm,
          emotion: selectedEmotion,
          show_encrypted: showEncrypted
        }
      }
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `codette-cocoons-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getEmotionColor = (emotion: string) => 
    EMOTION_COLORS[emotion as keyof typeof EMOTION_COLORS] || '#8B5CF6';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-lg overflow-hidden`}>
      {/* Header */}
      <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold flex items-center">
              <Package className="mr-2" size={18} />
              Quantum Cocoon Manager
            </h2>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Manage and explore emotional memory cocoons
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={exportCocoons}
              className={`p-2 rounded-md ${
                darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
              }`}
              title="Export Cocoons"
            >
              <Download size={16} />
            </button>
            {isAdmin && (
              <button
                onClick={() => setShowCreateForm(true)}
                className={`p-2 rounded-md ${
                  darkMode 
                    ? 'bg-purple-600 hover:bg-purple-700 text-white' 
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
                }`}
                title="Create New Cocoon"
              >
                <Plus size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="p-4 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            placeholder="Search cocoons..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full pl-10 pr-4 py-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-purple-500`}
          />
        </div>

        {/* Filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <select
              value={selectedEmotion}
              onChange={(e) => setSelectedEmotion(e.target.value)}
              className={`px-3 py-2 rounded-lg border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              } focus:outline-none focus:ring-2 focus:ring-purple-500`}
            >
              <option value="all">All Emotions</option>
              {Object.keys(EMOTION_COLORS).map(emotion => (
                <option key={emotion} value={emotion}>
                  {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowEncrypted(!showEncrypted)}
              className={`flex items-center px-3 py-2 rounded-lg border ${
                showEncrypted
                  ? darkMode
                    ? 'bg-purple-600 border-purple-600 text-white'
                    : 'bg-purple-500 border-purple-500 text-white'
                  : darkMode
                    ? 'bg-gray-700 border-gray-600 text-gray-300'
                    : 'bg-white border-gray-300 text-gray-700'
              }`}
            >
              {showEncrypted ? <Eye size={16} /> : <EyeOff size={16} />}
              <span className="ml-2 text-sm">Encrypted</span>
            </button>
          </div>

          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {filteredCocoons.length} of {cocoons.length} cocoons
          </div>
        </div>
      </div>

      {/* Cocoon List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          <AnimatePresence>
            {filteredCocoons.map((cocoon) => (
              <motion.div
                key={cocoon.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedCocoon?.id === cocoon.id
                    ? darkMode
                      ? 'border-purple-500 bg-purple-900/20'
                      : 'border-purple-500 bg-purple-50'
                    : darkMode
                      ? 'border-gray-700 bg-gray-750 hover:bg-gray-700'
                      : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
                onClick={() => setSelectedCocoon(cocoon)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: getEmotionColor(cocoon.emotion) }}
                      />
                      <h3 className="font-semibold text-sm truncate">
                        {cocoon.title}
                      </h3>
                      {cocoon.encrypted && (
                        <Lock size={12} className="text-yellow-500" />
                      )}
                    </div>
                    <p className={`text-xs mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {cocoon.summary}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {cocoon.tags.slice(0, 3).map((tag, index) => (
                        <span
                          key={index}
                          className={`px-2 py-1 text-xs rounded-full ${
                            darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                          }`}
                        >
                          {tag}
                        </span>
                      ))}
                      {cocoon.tags.length > 3 && (
                        <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          +{cocoon.tags.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end space-y-1">
                    <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {new Date(cocoon.created_at).toLocaleDateString()}
                    </div>
                    <div className="flex items-center space-x-1">
                      <div className="w-16 h-1 bg-gray-300 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            backgroundColor: getEmotionColor(cocoon.emotion),
                            width: `${cocoon.intensity * 100}%`
                          }}
                        />
                      </div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {Math.round(cocoon.intensity * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Selected Cocoon Detail */}
      <AnimatePresence>
        {selectedCocoon && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`border-t ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}
          >
            <div className="p-4">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-lg">{selectedCocoon.title}</h3>
                <button
                  onClick={() => setSelectedCocoon(null)}
                  className={`p-1 rounded-md ${
                    darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-200'
                  }`}
                >
                  <Eye size={16} />
                </button>
              </div>
              
              <p className={`text-sm mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {selectedCocoon.summary}
              </p>
              
              <blockquote className={`text-sm italic border-l-4 pl-3 mb-3 ${
                darkMode ? 'border-gray-600 text-gray-300' : 'border-gray-300 text-gray-700'
              }`}>
                "{selectedCocoon.quote}"
              </blockquote>
              
              <div className="flex flex-wrap gap-2">
                {selectedCocoon.tags.map((tag, index) => (
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default QuantumCocoonManager;