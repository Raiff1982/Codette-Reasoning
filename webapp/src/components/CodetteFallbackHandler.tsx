import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, RefreshCw, BrainCircuit, Volume2, VolumeX } from 'lucide-react';
import { useCodetteContext } from '@/core/hooks/useCodetteContext';
import { ExtensionManager } from '@/core/engine/ExtensionManager';
import { getPerspectiveColor } from '@/utils/perspectiveColors';
import { formatTimestamp, getTimeSince } from '@/utils/time';

function splitPerspective(p: string): string[] {
  return p
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .match(/[A-Z]?[a-z]+/g) || [p];
}

function getRecoverySuggestions(trace: string[]): string[] {
  const suggestions = new Set<string>();
  for (const entry of trace) {
    if (entry.toLowerCase().includes("network")) suggestions.add("Check internet connection or proxy settings.");
    if (entry.toLowerCase().includes("kaggle")) suggestions.add("Verify Kaggle API credentials and service availability.");
    if (entry.toLowerCase().includes("temporarily unavailable")) suggestions.add("Retry after a few minutes or fallback to offline mode.");
    if (entry.toLowerCase().includes("initialization failed")) suggestions.add("Reinitialize AI core modules using fallback-safe parameters.");
  }
  return Array.from(suggestions);
}

function calculateConfidence(cooldown: number, failures: number, network: string): { score: number; status: string } {
  let score = 100 - failures * 20;
  if (network === 'Offline') score -= 30;
  if (cooldown < 50) score -= 20;
  score = Math.max(0, Math.min(100, score));
  const status = score > 70 ? 'Stable' : score > 40 ? 'Moderate' : 'Critical';
  return { score, status };
}

export default function CodetteFallbackHandler() {
  const {
    recursionCount,
    activePerspectives,
    cocoonTrace,
    lastStableTimestamp,
    fallbackState,
    resetFallback
  } = useCodetteContext();

  const [cooldown, setCooldown] = useState(100);
  const [extensions, setExtensions] = useState<string[]>([]);
  const [systemStatus, setSystemStatus] = useState({
    network: 'Checking...',
    memoryUsage: 'Calculating...',
    cacheSize: 0,
    endpoint: 'Unknown'
  });
  const [failureCount, setFailureCount] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const recoverySuggestions = React.useMemo(() => getRecoverySuggestions(cocoonTrace), [cocoonTrace]);
  const confidence = React.useMemo(() => calculateConfidence(cooldown, failureCount, systemStatus.network), [cooldown, failureCount, systemStatus.network]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCooldown(prev => Math.max(prev - 1, 0));
    }, 80);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (fallbackState) {
      const loaded = ExtensionManager.listLoadedExtensions();
      setExtensions(loaded);

      setSystemStatus({
        network: navigator.onLine ? 'Online' : 'Offline',
        memoryUsage: `${(performance?.memory?.usedJSHeapSize / 1024 / 1024).toFixed(2) || 'N/A'} MB`,
        cacheSize: localStorage.length,
        endpoint: 'Supabase Kaggle Proxy'
      });

      const failureMessages = cocoonTrace.filter((entry) =>
        entry.toLowerCase().includes('failed') || entry.toLowerCase().includes('unavailable')
      );
      setFailureCount(failureMessages.length);

      const lastError = cocoonTrace[cocoonTrace.length - 1];
      if (typeof lastError === 'object' && lastError !== null) {
        const errorMeta = lastError;
        const traceInfo = `⚠️ Source: ${errorMeta.fileName || 'unknown'} [${errorMeta.lineNumber || '?'}:${errorMeta.columnNumber || '?'}]`;
        if (!cocoonTrace.includes(traceInfo)) {
          cocoonTrace.push(traceInfo);
        }
      }
    }
  }, [fallbackState, cocoonTrace]);

  const speakSummary = () => {
    const synth = window.speechSynthesis;
    if (!synth) return;

    let summary = `Fallback mode is active. Recursion count is ${recursionCount}. Confidence level is ${confidence.status}. ` +
      (recoverySuggestions.length > 0 ? `Suggested actions include: ${recoverySuggestions.join(', ')}.` : 'No recovery suggestions available.');

    if (cocoonTrace.length > 0) {
      const last = cocoonTrace[cocoonTrace.length - 1];
      if (typeof last === 'string' && last.startsWith('⚠️ Source:')) {
        summary += ' Last error originated from ' + last.replace('⚠️ Source: ', '') + '.';
      }
    }

    const utterance = new SpeechSynthesisUtterance(summary);
    utterance.onend = () => setIsSpeaking(false);
    synth.cancel();
    synth.speak(utterance);
    setIsSpeaking(true);
  };

  const handleReboot = useCallback(() => {
    resetFallback();
    ExtensionManager.flushSandbox();
    ExtensionManager.reinitializeSafeModules();
  }, [resetFallback]);

  return (
    <div className="grid gap-4 p-4">
      <div className="flex justify-end items-center">
        <button 
          onClick={speakSummary} 
          className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
        >
          {isSpeaking ? <VolumeX size={16} /> : <Volume2 size={16} />} Speak Summary
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-start gap-4">
          <AlertTriangle className="text-yellow-500 mt-1" />
          <div className="flex-1">
            <p className="text-base font-bold dark:text-yellow-100">Codette: Fallback Mode Activated</p>
            <p className="text-xs text-gray-700 dark:text-gray-300">Network connectivity issues detected. Engaging stabilization protocols.</p>
            
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="font-bold mb-2 text-sm">System Status</p>
                <ul className="space-y-1 text-sm">
                  <li className="flex items-center justify-between">
                    <span>Network:</span>
                    <span className={systemStatus.network === 'Online' ? 'text-green-500' : 'text-red-500'}>
                      {systemStatus.network}
                    </span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Memory Usage:</span>
                    <span>{systemStatus.memoryUsage}</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Cache Size:</span>
                    <span>{systemStatus.cacheSize} items</span>
                  </li>
                </ul>
              </div>
              
              <div>
                <p className="font-bold mb-2 text-sm">Recovery Status</p>
                <ul className="space-y-1 text-sm">
                  <li className="flex items-center justify-between">
                    <span>Recursion Count:</span>
                    <span>{recursionCount}</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Confidence:</span>
                    <span className={
                      confidence.score > 70 ? 'text-green-500' : 
                      confidence.score > 40 ? 'text-yellow-500' : 
                      'text-red-500'
                    }>
                      {confidence.score}% ({confidence.status})
                    </span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Cooldown:</span>
                    <span>{cooldown}%</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="mt-6">
              <p className="font-bold mb-2 text-sm">Active Perspectives</p>
              <div className="flex flex-wrap gap-2">
                {activePerspectives.map((perspective, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-full text-xs text-white"
                    style={{ backgroundColor: getPerspectiveColor(perspective) }}
                  >
                    {splitPerspective(perspective).join(' ')}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <p className="font-bold mb-2 text-sm">Recovery Suggestions</p>
              <ul className="list-disc pl-4 space-y-1 text-sm">
                {recoverySuggestions.map((suggestion, i) => (
                  <li key={i}>{suggestion}</li>
                ))}
              </ul>
            </div>

            <div className="mt-6">
              <p className="font-bold mb-2 text-sm">Error Trace</p>
              <div className="bg-gray-100 dark:bg-gray-900 rounded-md p-3 max-h-40 overflow-y-auto">
                {cocoonTrace.map((trace, i) => (
                  <p key={i} className="text-xs font-mono mb-1">{trace}</p>
                ))}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm">
                <span className="text-gray-600 dark:text-gray-400">Last Stable: </span>
                <span>{formatTimestamp(lastStableTimestamp)}</span>
                <span className="text-gray-500 dark:text-gray-500 ml-2">
                  ({getTimeSince(lastStableTimestamp)})
                </span>
              </div>
              
              <button
                onClick={handleReboot}
                disabled={cooldown > 0}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  cooldown > 0
                    ? 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                <RefreshCw size={16} className={cooldown > 0 ? 'animate-spin' : ''} />
                Force Reboot
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}