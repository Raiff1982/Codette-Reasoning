import React, { useState, useRef, useEffect } from 'react';
import { Send, Circle, Bot, User, Sparkles, Brain } from 'lucide-react';
import { CodetteResponseCard, CodetteResponse } from './CodetteComponents';

interface Message {
  role: string;
  content: string;
  timestamp: Date;
  metadata?: CodetteResponse;
}

interface ChatInterfaceProps {
  messages: Message[];
  sendMessage: (content: string) => void;
  isProcessing: boolean;
  darkMode: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  messages, 
  sendMessage, 
  isProcessing,
  darkMode
}) => {
  const [input, setInput] = useState('');
  const [isDreamMode, setIsDreamMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      const finalInput = isDreamMode ? `dream about ${input.trim()}` : input.trim();
      sendMessage(finalInput);
      setInput('');
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleDreamMode = () => {
    setIsDreamMode(!isDreamMode);
    if (!isDreamMode) {
      inputRef.current?.focus();
    }
  };
  
  return (
    <div className={`flex-1 flex flex-col ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg rounded-lg overflow-hidden transition-colors duration-300`}>
      <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <h2 className="text-lg font-semibold flex items-center">
          <Bot className="mr-2" size={18} />
          Conversation with Codette
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && message.metadata ? (
              <CodetteResponseCard response={message.metadata} />
            ) : (
              <div 
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.role === 'user' 
                    ? darkMode 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-blue-100 text-blue-900'
                    : message.role === 'system'
                      ? darkMode
                        ? 'bg-red-900 text-white'
                        : 'bg-red-100 text-red-900'
                      : darkMode
                        ? 'bg-gray-700 text-white'
                        : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="flex items-start mb-1">
                  {message.role === 'user' ? (
                    <User className="mr-2 mt-1" size={14} />
                  ) : message.role === 'system' ? (
                    <Circle className="mr-2 mt-1" size={14} />
                  ) : (
                    <Bot className="mr-2 mt-1" size={14} />
                  )}
                  <div className="text-sm font-semibold">
                    {message.role === 'user' ? 'You' : message.role === 'system' ? 'System' : 'Codette'}
                  </div>
                </div>
                <div className="whitespace-pre-wrap">
                  {message.content}
                </div>
                <div className="text-xs opacity-70 mt-1 text-right">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            )}
          </div>
        ))}
        
        {isProcessing && (
          <div className="flex justify-start">
            <div className={`rounded-lg p-3 ${
              darkMode ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-900'
            }`}>
              <div className="flex items-center">
                <Bot className="mr-2" size={14} />
                <div className="text-sm font-semibold">Codette</div>
              </div>
              <div className="flex items-center mt-2">
                <div className="flex space-x-1">
                  <div className="typing-dot h-2 w-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></div>
                  <div className="typing-dot h-2 w-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></div>
                  <div className="typing-dot h-2 w-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '600ms' }}></div>
                </div>
                <div className="ml-3 text-sm italic opacity-70">
                  {isDreamMode ? 'Weaving dreams through quantum threads...' : 'Processing through recursive thought loops...'}
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <form 
        onSubmit={handleSubmit} 
        className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}
      >
        <div className="flex items-center mb-2">
          <button
            type="button"
            onClick={toggleDreamMode}
            className={`flex items-center px-3 py-1 rounded-full text-sm transition-colors ${
              isDreamMode
                ? darkMode
                  ? 'bg-purple-600 text-white'
                  : 'bg-purple-100 text-purple-900'
                : darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {isDreamMode ? (
              <>
                <Sparkles size={14} className="mr-1" />
                Dreamweaver Active
              </>
            ) : (
              <>
                <Brain size={14} className="mr-1" />
                Enable Dreamweaver
              </>
            )}
          </button>
        </div>
        
        <div className="flex">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isDreamMode ? "Enter a concept for Codette to dream about..." : "Ask Codette anything..."}
            className={`flex-1 resize-none border rounded-lg p-2 focus:outline-none focus:ring-2 ${
              isDreamMode
                ? 'focus:ring-purple-500'
                : 'focus:ring-blue-500'
            } ${
              darkMode 
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            }`}
            rows={2}
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className={`ml-2 p-2 rounded-lg transition-colors ${
              !input.trim() || isProcessing
                ? darkMode 
                  ? 'bg-gray-700 text-gray-500' 
                  : 'bg-gray-200 text-gray-400'
                : isDreamMode
                  ? darkMode
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-purple-500 text-white hover:bg-purple-600'
                  : darkMode
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            <Send size={20} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;