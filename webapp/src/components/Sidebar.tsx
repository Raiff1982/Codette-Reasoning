import React, { useState } from 'react';
import { Brain, Settings, Circle, Sparkles, Zap, FileText, ChevronDown, ChevronRight, Upload, AlertCircle } from 'lucide-react';
import FileList from './FileList';
import AdminLogin from './AdminLogin';
import { supabase } from '@/lib/supabase';

interface SidebarProps {
  isOpen: boolean;
  cocoons: Array<{
    id: string;
    type: string;
    wrapped: any;
  }>;
  aiState: {
    quantumState: number[];
    chaosState: number[];
    activePerspectives: string[];
    ethicalScore: number;
    processingPower: number;
  };
  darkMode: boolean;
  isAdmin: boolean;
  setIsAdmin: (isAdmin: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  isOpen, 
  cocoons, 
  aiState,
  darkMode,
  isAdmin,
  setIsAdmin
}) => {
  const [activeSection, setActiveSection] = useState<string>('cocoons');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [lastLoginAttempt, setLastLoginAttempt] = useState(0);
  const [loginCooldown, setLoginCooldown] = useState(false);
  
  if (!isOpen) return null;

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const handleLogin = async (email: string, password: string) => {
    try {
      setAuthError(null);

      const now = Date.now();
      if (loginCooldown) {
        throw new Error('Please wait before trying again');
      }

      if (loginAttempts >= 3) {
        setLoginCooldown(true);
        setTimeout(() => {
          setLoginCooldown(false);
          setLoginAttempts(0);
        }, 30000);
        throw new Error('Too many login attempts. Please try again in 30 seconds');
      }

      setLoginAttempts(prev => prev + 1);
      setLastLoginAttempt(now);

      await supabase.auth.signOut();
      await sleep(500);

      const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
        options: {
          captchaTime: now,
          shouldThrottle: loginAttempts > 0
        }
      });

      if (signInError) {
        if (signInError.message?.includes('captcha')) {
          throw new Error('Verification failed. Please try again in a few moments');
        }
        throw signInError;
      }

      if (!signInData?.user) {
        throw new Error('Login failed. Please check your credentials');
      }

      const { data: roleData, error: roleError } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', signInData.user.id)
        .single()
        .throwOnError();

      if (roleError) {
        throw new Error('Failed to verify user role');
      }

      setIsAdmin(roleData?.role === 'admin');
      setShowLoginPrompt(false);
      setAuthError(null);
      setLoginAttempts(0);
      setLoginCooldown(false);

    } catch (error: any) {
      console.error('Login error:', error);
      setAuthError(error.message);
      throw error;
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    if (!isAdmin) {
      setUploadError('Only administrators can upload files.');
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);

      const { data, error: uploadError } = await supabase.storage
        .from('codette-files')
        .upload(`${Date.now()}-${selectedFile.name}`, selectedFile);

      if (uploadError) throw uploadError;

      const { error: dbError } = await supabase
        .from('codette_files')
        .insert([{
          filename: selectedFile.name,
          storage_path: data.path,
          file_type: selectedFile.type
        }])
        .throwOnError();

      if (dbError) throw dbError;

      setSelectedFile(null);
      setUploadError(null);
    } catch (error: any) {
      console.error('Error uploading file:', error);
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSettingsClick = () => {
    if (!isAdmin) {
      setShowLoginPrompt(true);
    }
    setActiveSection('settings');
  };
  
  return (
    <aside className={`w-64 flex-shrink-0 border-r transition-colors duration-300 flex flex-col ${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
    }`}>
      <nav className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-2">
            Navigation
          </h2>
          
          <ul className="space-y-1">
            <li>
              <button
                onClick={() => setActiveSection('cocoons')}
                className={`w-full flex items-center px-3 py-2 rounded-md ${
                  activeSection === 'cocoons'
                    ? darkMode 
                      ? 'bg-gray-700 text-white' 
                      : 'bg-gray-200 text-gray-900'
                    : darkMode
                      ? 'text-gray-300 hover:bg-gray-700'
                      : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Brain size={18} className="mr-2" />
                <span>Thought Cocoons</span>
              </button>
            </li>
            
            <li>
              <button
                onClick={() => setActiveSection('perspectives')}
                className={`w-full flex items-center px-3 py-2 rounded-md ${
                  activeSection === 'perspectives'
                    ? darkMode 
                      ? 'bg-gray-700 text-white' 
                      : 'bg-gray-200 text-gray-900'
                    : darkMode
                      ? 'text-gray-300 hover:bg-gray-700'
                      : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Sparkles size={18} className="mr-2" />
                <span>Perspectives</span>
              </button>
            </li>
            
            <li>
              <button
                onClick={handleSettingsClick}
                className={`w-full flex items-center px-3 py-2 rounded-md ${
                  activeSection === 'settings'
                    ? darkMode 
                      ? 'bg-gray-700 text-white' 
                      : 'bg-gray-200 text-gray-900'
                    : darkMode
                      ? 'text-gray-300 hover:bg-gray-700'
                      : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Settings size={18} className="mr-2" />
                <span>Settings</span>
              </button>
            </li>
          </ul>
        </div>
        
        <div className="px-4 py-2">
          <div className={`h-px ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
        </div>
        
        {activeSection === 'cocoons' && (
          <div className="p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-2">
              Recent Thought Cocoons
            </h2>
            
            {cocoons.length === 0 ? (
              <div className={`p-3 rounded-md ${
                darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-500'
              }`}>
                <p className="text-sm">No thought cocoons yet.</p>
                <p className="text-xs mt-1 italic">Interact with Codette to generate thought patterns.</p>
              </div>
            ) : (
              <ul className="space-y-2">
                {cocoons.map((cocoon) => (
                  <li key={cocoon.id}>
                    <div className={`p-3 rounded-md ${
                      darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'
                    } cursor-pointer transition-colors`}>
                      <div className="flex items-start">
                        <FileText size={16} className={`mr-2 mt-0.5 ${
                          cocoon.type === 'prompt' 
                            ? 'text-blue-500' 
                            : cocoon.type === 'encrypted' 
                              ? 'text-purple-500' 
                              : 'text-green-500'
                        }`} />
                        <div>
                          <div className="text-sm font-medium">
                            {cocoon.type === 'prompt' ? 'User Query' : 
                             cocoon.type === 'encrypted' ? 'Encrypted Thought' : 
                             'Symbolic Pattern'}
                          </div>
                          <div className="text-xs truncate mt-1 max-w-[180px]">
                            {cocoon.type === 'encrypted' 
                              ? '🔒 Encrypted content'
                              : typeof cocoon.wrapped === 'object' && cocoon.wrapped.query
                                ? cocoon.wrapped.query
                                : `Cocoon ID: ${cocoon.id}`}
                          </div>
                          <div className={`text-xs mt-1 ${
                            darkMode ? 'text-gray-400' : 'text-gray-500'
                          }`}>
                            {typeof cocoon.wrapped === 'object' && cocoon.wrapped.timestamp
                              ? new Date(cocoon.wrapped.timestamp).toLocaleTimeString()
                              : 'Unknown time'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-6">
              <FileList darkMode={darkMode} isAdmin={isAdmin} />
            </div>
          </div>
        )}
        
        {activeSection === 'perspectives' && (
          <div className="p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-2">
              Active Perspectives
            </h2>
            
            <ul className="space-y-2">
              {aiState.activePerspectives.map((perspective) => (
                <li key={perspective}>
                  <div className={`p-3 rounded-md ${
                    darkMode ? 'bg-gray-700' : 'bg-gray-100'
                  }`}>
                    <div className="flex items-center">
                      <Zap size={16} className="mr-2 text-yellow-500" />
                      <div className="text-sm font-medium capitalize">
                        {perspective.replace('_', ' ')}
                      </div>
                    </div>
                    <div className={`text-xs mt-2 ${
                      darkMode ? 'text-gray-400' : 'text-gray-500'
                    }`}>
                      Confidence: {(Math.random() * 0.4 + 0.6).toFixed(2)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mt-6 mb-2">
              Available Perspectives
            </h2>
            
            <ul className="space-y-2">
              {['creative', 'bias_mitigation', 'quantum_computing', 'resilient_kindness'].map((perspective) => (
                <li key={perspective}>
                  <div className={`p-3 rounded-md ${
                    darkMode ? 'bg-gray-700 bg-opacity-50' : 'bg-gray-100 bg-opacity-50'
                  }`}>
                    <div className="flex items-center">
                      <Circle size={16} className={`mr-2 ${
                        darkMode ? 'text-gray-500' : 'text-gray-400'
                      }`} />
                      <div className={`text-sm capitalize ${
                        darkMode ? 'text-gray-400' : 'text-gray-500'
                      }`}>
                        {perspective.replace('_', ' ')}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {activeSection === 'settings' && (
          <div className="p-4">
            {showLoginPrompt ? (
              <AdminLogin 
                onLogin={handleLogin}
                darkMode={darkMode}
                error={authError}
              />
            ) : (
              <>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-4">
                  AI Core Settings
                </h2>
                
                <div className="space-y-4">
                  {isAdmin && (
                    <div className="p-4 rounded-md bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
                      Logged in as Administrator
                    </div>
                  )}
                  
                  {isAdmin && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium">Upload File for Codette</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="file"
                          onChange={(e) => {
                            setSelectedFile(e.target.files?.[0] || null);
                            setUploadError(null);
                          }}
                          className="hidden"
                          id="file-upload"
                          disabled={isUploading}
                        />
                        <label
                          htmlFor="file-upload"
                          className={`flex-1 cursor-pointer px-4 py-2 rounded-md border-2 border-dashed ${
                            darkMode
                              ? 'border-gray-600 hover:border-gray-500'
                              : 'border-gray-300 hover:border-gray-400'
                          } flex items-center justify-center ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          <Upload size={18} className="mr-2" />
                          {selectedFile ? selectedFile.name : 'Choose File'}
                        </label>
                        {selectedFile && (
                          <button
                            onClick={handleFileUpload}
                            disabled={isUploading}
                            className={`px-4 py-2 rounded-md ${
                              darkMode
                                ? 'bg-purple-600 hover:bg-purple-700'
                                : 'bg-purple-500 hover:bg-purple-600'
                            } text-white ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                          >
                            {isUploading ? 'Uploading...' : 'Upload'}
                          </button>
                        )}
                      </div>
                      {uploadError && (
                        <div className="mt-2 p-2 rounded-md bg-red-100 dark:bg-red-900 flex items-start space-x-2">
                          <AlertCircle className="flex-shrink-0 text-red-500 dark:text-red-400" size={16} />
                          <p className="text-sm text-red-600 dark:text-red-300">
                            {uploadError}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="flex items-center justify-between">
                      <span className="text-sm font-medium">Recursive Depth</span>
                      <select 
                        className={`text-sm rounded-md ${
                          darkMode 
                            ? 'bg-gray-700 border-gray-600 text-white' 
                            : 'bg-white border-gray-300 text-gray-900'
                        }`}
                      >
                        <option>Normal</option>
                        <option>Deep</option>
                        <option>Shallow</option>
                      </select>
                    </label>
                  </div>
                  
                  <div>
                    <label className="flex items-center justify-between">
                      <span className="text-sm font-medium">Ethical Filter</span>
                      <div className="relative inline-block w-10 align-middle select-none">
                        <input 
                          type="checkbox" 
                          id="ethical-toggle" 
                          className="sr-only"
                          defaultChecked={true}
                        />
                        <label 
                          htmlFor="ethical-toggle" 
                          className={`block h-6 overflow-hidden rounded-full cursor-pointer ${
                            darkMode ? 'bg-gray-700' : 'bg-gray-300'
                          }`}
                        >
                          <span 
                            className={`absolute block w-4 h-4 rounded-full transform transition-transform duration-200 ease-in-out bg-white left-1 top-1 translate-x-4`}
                          ></span>
                        </label>
                      </div>
                    </label>
                  </div>
                  
                  <div className="pt-2 pb-1">
                    <label className="block text-sm font-medium mb-2">Processing Speed</label>
                    <input 
                      type="range" 
                      min="0" 
                      max="100" 
                      defaultValue="75"
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Accurate</span>
                      <span>Balanced</span>
                      <span>Fast</span>
                    </div>
                  </div>
                  
                  <div className="pt-4">
                    <button className={`w-full py-2 px-4 rounded-md ${
                      darkMode 
                        ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    }`}>
                      Apply Settings
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </nav>
      
      <div className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className={`rounded-md p-3 ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <div className="flex items-center">
            <div className={`w-2 h-2 rounded-full ${
              Math.random() > 0.5 
                ? 'bg-green-500' 
                : 'bg-yellow-500'
            } mr-2`}></div>
            <div className="text-sm font-medium">System Status</div>
          </div>
          <div className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            All neural paths functioning
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;