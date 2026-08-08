import React, { useState, useEffect, useRef } from 'react';
import { Zap, Brain, Settings, Moon, ChevronRight, Send, Bot, Server, Sparkles, Circle, User } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import VisualizationPanel from './components/VisualizationPanel';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import QuantumDashboard from './components/QuantumDashboard';
import CognitionCocooner from './services/CognitionCocooner';
import AICore from './services/AICore';
import { CodetteResponse } from './components/CodetteComponents';
import { CodetteContext } from './core/hooks/useCodetteContext';
import CodetteFallbackHandler from './components/CodetteFallbackHandler';
import { AuthProvider, useAuth } from './core/providers/AuthProvider';
import { supabase } from './lib/supabase';

interface Message {
  role: string;
  content: string;
  timestamp: Date;
  metadata?: CodetteResponse;
}

function AppContent() {
  const { isAuthenticated, isLoading, error, role, signIn } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [aiState, setAiState] = useState({
    quantumState: [0.3, 0.7, 0.5],
    chaosState: [0.2, 0.8, 0.4, 0.6],
    activePerspectives: ['newton', 'davinci', 'neural_network', 'philosophical'],
    ethicalScore: 0.93,
    processingPower: 0.72
  });
  const [cocoons, setCocoons] = useState<Array<{id: string, type: string, wrapped: any}>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [fallbackState, setFallbackState] = useState(false);
  const [recursionCount, setRecursionCount] = useState(0);
  const [lastStableTimestamp, setLastStableTimestamp] = useState(Date.now());
  const [cocoonTrace, setCocoonTrace] = useState<string[]>([]);
  const [authRetryCount, setAuthRetryCount] = useState(0);
  const [viewMode, setViewMode] = useState<'classic' | 'quantum'>('quantum');
  const maxAuthRetries = 5;
  const authRetryDelay = (attempt: number) => Math.min(2000 * Math.pow(2, attempt), 30000);
  
  const aiCore = useRef(new AICore());
  const cocooner = useRef(new CognitionCocooner());

  useEffect(() => {
    let retryTimeout: number;
    let isSubscribed = true;

    const autoSignIn = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        
        if (!session && signIn && authRetryCount < maxAuthRetries && isSubscribed) {
          console.log(`Attempting auto sign-in (attempt ${authRetryCount + 1}/${maxAuthRetries})`);
          
          const response = await signIn('admin@codette.ai', 'admin123');
          
          if (response?.error?.message?.includes('captcha')) {
            console.warn('CAPTCHA verification required. Implementing exponential backoff...');
            setAuthRetryCount(prev => prev + 1);
            retryTimeout = window.setTimeout(autoSignIn, authRetryDelay(authRetryCount));
            return;
          }
        }
      } catch (error: any) {
        console.error('Auto sign-in failed:', error);
        
        if (error.message?.includes('captcha') && authRetryCount < maxAuthRetries && isSubscribed) {
          console.warn('CAPTCHA error, implementing exponential backoff...');
          setAuthRetryCount(prev => prev + 1);
          retryTimeout = window.setTimeout(autoSignIn, authRetryDelay(authRetryCount));
          return;
        }
        
        setFallbackState(true);
        setRecursionCount(prev => prev + 1);
        setCocoonTrace(prev => [...prev, `Authentication failed: ${error.message}`]);
      }
    };

    if (!isAuthenticated && !isLoading) {
      autoSignIn();
    }

    return () => {
      isSubscribed = false;
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
    };
  }, [signIn, isAuthenticated, isLoading, authRetryCount]);

  useEffect(() => {
    setIsAdmin(role === 'admin');
  }, [role]);

  useEffect(() => {
    const initializeAI = async () => {
      if (!isAuthenticated) {
        return;
      }

      try {
        await aiCore.current.initialize();
      } catch (error) {
        console.error('Failed to initialize AI:', error);
        setFallbackState(true);
        setRecursionCount(prev => prev + 1);
        setCocoonTrace(prev => [...prev, `AI initialization failed: ${error.message}`]);
      }
    };

    if (isAuthenticated) {
      initializeAI();
    }
  }, [isAuthenticated]);
  
  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: 'Hello! I am Codette, an advanced AI assistant with quantum spiderweb cognition, recursive reasoning, and multi-agent intelligence. I can explore emotional memory networks and perform quantum reflections. How can I assist you today?',
        timestamp: new Date(),
        metadata: {
          text: 'Hello! I am Codette, an advanced AI assistant with quantum spiderweb cognition, recursive reasoning, and multi-agent intelligence. I can explore emotional memory networks and perform quantum reflections. How can I assist you today?',
          instabilityFlag: false,
          perspectivesUsed: ['greeting', 'introduction', 'quantum'],
          cocoonLog: ['Initializing Codette AI...', 'Quantum state stabilized', 'Emotional webs activated'],
          forceRefresh: () => handleForceRefresh('Hello! I am Codette, an advanced AI assistant with quantum spiderweb cognition, recursive reasoning, and multi-agent intelligence. I can explore emotional memory networks and perform quantum reflections. How can I assist you today?')
        }
      }
    ]);
  }, []);
  
  const handleForceRefresh = async (content: string) => {
    setIsProcessing(true);
    try {
      const response = await aiCore.current.processInput(content, true);
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: response,
        timestamp: new Date(),
        metadata: {
          text: response,
          instabilityFlag: Math.random() > 0.8,
          perspectivesUsed: aiState.activePerspectives.slice(0, 3),
          cocoonLog: [`Regenerating response for: ${content}`, `Generated new response at ${new Date().toISOString()}`],
          forceRefresh: () => handleForceRefresh(content)
        }
      };
      
      setMessages(prev => [...prev.slice(0, -1), assistantMessage]);
    } catch (error) {
      console.error('Error regenerating response:', error);
      setFallbackState(true);
      setRecursionCount(prev => prev + 1);
      setCocoonTrace(prev => [...prev, `Response regeneration failed: ${error.message}`]);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };
  
  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };
  
  const resetFallback = () => {
    setFallbackState(false);
    setRecursionCount(0);
    setLastStableTimestamp(Date.now());
    setCocoonTrace([]);
    setAuthRetryCount(0);
  };
  
  const sendMessage = async (content: string) => {
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const thought = { query: content, timestamp: new Date() };
      const cocoonId = cocooner.current.wrap(thought);
      setCocoons(prev => [...prev, { 
        id: cocoonId, 
        type: 'prompt', 
        wrapped: thought 
      }]);
      
      const response = await aiCore.current.processInput(content);
      
      setAiState(prev => ({
        ...prev,
        quantumState: [Math.random(), Math.random(), Math.random()].map(v => v.toFixed(2)).map(Number),
        chaosState: [Math.random(), Math.random(), Math.random(), Math.random()].map(v => v.toFixed(2)).map(Number),
        ethicalScore: Number((prev.ethicalScore + Math.random() * 0.1 - 0.05).toFixed(2)),
        processingPower: Number((prev.processingPower + Math.random() * 0.1 - 0.05).toFixed(2))
      }));
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: response,
        timestamp: new Date(),
        metadata: {
          text: response,
          instabilityFlag: Math.random() > 0.8,
          perspectivesUsed: aiState.activePerspectives.slice(0, 3),
          cocoonLog: [`Processing query: ${content}`, `Generated response at ${new Date().toISOString()}`, 'Quantum spiderweb activated'],
          forceRefresh: () => handleForceRefresh(content)
        }
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error processing message:', error);
      setFallbackState(true);
      setRecursionCount(prev => prev + 1);
      setCocoonTrace(prev => [...prev, `Message processing failed: ${error.message}`]);
      
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'An error occurred while processing your request. My quantum state needs recalibration.',
        timestamp: new Date()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const contextValue = {
    recursionCount,
    activePerspectives: aiState.activePerspectives,
    cocoonTrace,
    lastStableTimestamp,
    fallbackState,
    resetFallback
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }
  
  return (
    <CodetteContext.Provider value={contextValue}>
      <div className={`flex flex-col h-screen transition-colors duration-300 ${darkMode ? 'dark bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
        <Header 
          toggleSidebar={toggleSidebar}
          toggleDarkMode={toggleDarkMode} 
          darkMode={darkMode} 
          aiState={aiState}
        />
        
        <div className="flex flex-1 overflow-hidden">
          <Sidebar 
            isOpen={sidebarOpen} 
            cocoons={cocoons} 
            aiState={aiState}
            darkMode={darkMode}
            isAdmin={isAdmin}
            setIsAdmin={setIsAdmin}
          />
          
          <main className="flex-1 flex flex-col overflow-hidden">
            {fallbackState ? (
              <CodetteFallbackHandler />
            ) : (
              <div className="flex-1 overflow-hidden">
                {viewMode === 'quantum' ? (
                  <QuantumDashboard
                    messages={messages}
                    sendMessage={sendMessage}
                    isProcessing={isProcessing}
                    darkMode={darkMode}
                    isAdmin={isAdmin}
                    aiState={aiState}
                  />
                ) : (
                  <div className="flex h-full">
                    <ChatInterface 
                      messages={messages} 
                      sendMessage={sendMessage} 
                      isProcessing={isProcessing}
                      darkMode={darkMode}
                    />
                    
                    <VisualizationPanel 
                      aiState={aiState} 
                      darkMode={darkMode}
                    />
                  </div>
                )}
              </div>
            )}
          </main>
        </div>

        {/* View Mode Toggle */}
        <div className="fixed bottom-4 right-4 z-50">
          <button
            onClick={() => setViewMode(viewMode === 'classic' ? 'quantum' : 'classic')}
            className={`px-4 py-2 rounded-full shadow-lg transition-all ${
              darkMode
                ? 'bg-purple-600 hover:bg-purple-700 text-white'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
            }`}
          >
            {viewMode === 'classic' ? (
              <>
                <Zap className="inline mr-2" size={16} />
                Quantum Mode
              </>
            ) : (
              <>
                <Brain className="inline mr-2" size={16} />
                Classic Mode
              </>
            )}
          </button>
        </div>
      </div>
    </CodetteContext.Provider>
  );
}

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;