import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Bot, ListOrdered, Activity } from 'lucide-react';
import ChatInterface from './ChatInterface';
import { CodetteResponseCard, CodetteResponse } from './CodetteComponents';

interface Message {
  role: string;
  content: string;
  timestamp: Date;
  metadata?: CodetteResponse;
}

export default function CodetteDashboard({
  messages,
  sendMessage,
  isProcessing,
  darkMode
}: {
  messages: Message[];
  sendMessage: (content: string) => void;
  isProcessing: boolean;
  darkMode: boolean;
}) {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="flex flex-col h-full w-full p-4 space-y-4">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="chat" className="flex items-center">
            <Bot className="w-4 h-4 mr-2" /> Chat
          </TabsTrigger>
          <TabsTrigger value="memory" className="flex items-center">
            <ListOrdered className="w-4 h-4 mr-2" /> Memory
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center">
            <Activity className="w-4 h-4 mr-2" /> System
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="h-[calc(100vh-12rem)] overflow-hidden">
          <ChatInterface
            messages={messages}
            sendMessage={sendMessage}
            isProcessing={isProcessing}
            darkMode={darkMode}
          />
        </TabsContent>

        <TabsContent value="memory">
          <div className="p-4 rounded-xl bg-white dark:bg-gray-800 shadow-lg">
            <h3 className="text-lg font-semibold mb-4 text-purple-700 dark:text-purple-300 flex items-center">
              <ListOrdered className="w-5 h-5 mr-2" />
              Cocoon Memory Logs
            </h3>
            <div className="space-y-4 max-h-[calc(100vh-16rem)] overflow-y-auto">
              {messages
                .filter(m => m.metadata?.cocoonLog?.length)
                .map((m, i) => (
                  <div key={i} className="transition-all hover:scale-[1.01]">
                    <CodetteResponseCard response={m.metadata!} />
                  </div>
                ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="system">
          <div className="p-4 rounded-xl bg-white dark:bg-gray-800 shadow-lg">
            <h3 className="text-lg font-semibold mb-4 text-blue-700 dark:text-blue-300 flex items-center">
              <Activity className="w-5 h-5 mr-2" />
              System Diagnostics
            </h3>
            <div className="space-y-4 max-h-[calc(100vh-16rem)] overflow-y-auto">
              {messages
                .filter(m => m.metadata)
                .slice(-5)
                .map((m, i) => (
                  <div key={i} className="transition-all hover:scale-[1.01]">
                    <CodetteResponseCard response={m.metadata!} />
                  </div>
                ))}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}