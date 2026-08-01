import React, { useState } from 'react';
import { Lock, AlertCircle, User } from 'lucide-react';

interface AdminLoginProps {
  onLogin: (email: string, password: string) => void;
  darkMode: boolean;
  error?: string | null;
}

const AdminLogin: React.FC<AdminLoginProps> = ({ onLogin, darkMode, error }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await onLogin(email, password);
    } catch (err: any) {
      // Error is handled by the parent component
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`p-6 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
      <div className="flex items-center justify-center mb-6">
        <User className={`${darkMode ? 'text-blue-400' : 'text-blue-600'} w-12 h-12`} />
      </div>
      <h2 className={`text-xl font-bold text-center mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        Sign In
      </h2>
      <p className={`text-sm text-center mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
        Please enter your credentials to access the system
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            className={`w-full px-4 py-2 rounded-md border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            disabled={isLoading}
            required
          />
        </div>
        <div>
          <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            className={`w-full px-4 py-2 rounded-md border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            disabled={isLoading}
            required
          />
        </div>
        
        {error && (
          <div className="mt-2 p-2 rounded-md bg-red-100 dark:bg-red-900 flex items-start space-x-2">
            <AlertCircle className="flex-shrink-0 text-red-500 dark:text-red-400" size={16} />
            <p className="text-sm text-red-600 dark:text-red-300">
              {error}
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-2 px-4 rounded-md ${
            darkMode
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          } transition-colors duration-200 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isLoading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
};

export default AdminLogin;