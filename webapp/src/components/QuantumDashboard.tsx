import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Network, Package, Brain, Activity, Zap } from 'lucide-react';
import QuantumSpiderwebPanel from './QuantumSpiderwebPanel';
import QuantumCocoonManager from './QuantumCocoonManager';
import ChatInterface from './ChatInterface';
import VisualizationPanel from './VisualizationPanel';

interface Message {
  role: string;
  content: string;
  timestamp: Date;
  metadata?: any;
}

interface QuantumDashboardProps {
  messages: Message[];
  sendMessage: (content: string) => void;
  isProcessing: boolean;
  darkMode: boolean;
  isAdmin: boolean;
  aiState: {
    quantumState: number[];
    chaosState: number[];
    activePerspectives: string[];
    ethicalScore: number;
    processingPower: number;
  };
}

const QuantumDashboard: React.FC<QuantumDashboardProps> = ({
  messages,
  sendMessage,
  isProcessing,
  darkMode,
  isAdmin,
  aiState
}) => {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="flex flex-col h-full w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full h-full flex flex-col">
        <div className="flex-shrink-0 p-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="chat" className="flex items-center">
              <Brain className="w-4 h-4 mr-2" /> Chat
            </TabsTrigger>
            <TabsTrigger value="spiderweb" className="flex items-center">
              <Network className="w-4 h-4 mr-2" /> Spiderweb
            </TabsTrigger>
            <TabsTrigger value="cocoons" className="flex items-center">
              <Package className="w-4 h-4 mr-2" /> Cocoons
            </TabsTrigger>
            <TabsTrigger value="quantum" className="flex items-center">
              <Zap className="w-4 h-4 mr-2" /> Quantum
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="chat" className="h-full m-0 p-4">
            <div className="flex h-full space-x-4">
              <div className="flex-1">
                <ChatInterface
                  messages={messages}
                  sendMessage={sendMessage}
                  isProcessing={isProcessing}
                  darkMode={darkMode}
                />
              </div>
              <div className="w-1/3">
                <VisualizationPanel
                  aiState={aiState}
                  darkMode={darkMode}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="spiderweb" className="h-full m-0 p-4">
            <div className="flex h-full space-x-4">
              <div className="flex-1">
                <QuantumSpiderwebPanel
                  darkMode={darkMode}
                  aiState={aiState}
                />
              </div>
              <div className="w-1/3">
                <div className={`h-full rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg p-4`}>
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <Activity className="mr-2" size={18} />
                    Quantum Metrics
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Entanglement Coherence</span>
                        <span className="text-sm font-semibold">
                          {Math.round(aiState.quantumState.reduce((a, b) => a + b, 0) / aiState.quantumState.length * 100)}%
                        </span>
                      </div>
                      <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}>
                        <div 
                          className="h-full rounded-full bg-purple-500"
                          style={{ 
                            width: `${Math.round(aiState.quantumState.reduce((a, b) => a + b, 0) / aiState.quantumState.length * 100)}%` 
                          }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Emotional Resonance</span>
                        <span className="text-sm font-semibold">
                          {Math.round(aiState.chaosState.reduce((a, b) => a + b, 0) / aiState.chaosState.length * 100)}%
                        </span>
                      </div>
                      <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}>
                        <div 
                          className="h-full rounded-full bg-cyan-500"
                          style={{ 
                            width: `${Math.round(aiState.chaosState.reduce((a, b) => a + b, 0) / aiState.chaosState.length * 100)}%` 
                          }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Ethical Alignment</span>
                        <span className="text-sm font-semibold">{Math.round(aiState.ethicalScore * 100)}%</span>
                      </div>
                      <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}>
                        <div 
                          className="h-full rounded-full bg-green-500"
                          style={{ width: `${Math.round(aiState.ethicalScore * 100)}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Processing Power</span>
                        <span className="text-sm font-semibold">{Math.round(aiState.processingPower * 100)}%</span>
                      </div>
                      <div className={`w-full h-2 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}>
                        <div 
                          className="h-full rounded-full bg-blue-500"
                          style={{ width: `${Math.round(aiState.processingPower * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="mt-6">
                    <h4 className="text-sm font-semibold mb-2">Active Perspectives</h4>
                    <div className="space-y-1">
                      {aiState.activePerspectives.map((perspective, index) => (
                        <div
                          key={index}
                          className={`text-xs px-2 py-1 rounded-full ${
                            darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                          }`}
                        >
                          {perspective.replace('_', ' ')}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="cocoons" className="h-full m-0 p-4">
            <QuantumCocoonManager
              darkMode={darkMode}
              isAdmin={isAdmin}
            />
          </TabsContent>

          <TabsContent value="quantum" className="h-full m-0 p-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
              <QuantumSpiderwebPanel
                darkMode={darkMode}
                aiState={aiState}
              />
              <VisualizationPanel
                aiState={aiState}
                darkMode={darkMode}
              />
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
};

export default QuantumDashboard;