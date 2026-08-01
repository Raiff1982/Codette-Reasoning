import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'npm:@supabase/supabase-js@2.39.3';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

interface FallbackRequest {
  recursionCount: number;
  cocoonTrace: string[];
  lastStableTimestamp: string;
  fallbackState: boolean;
}

const verifyAuth = async (req: Request) => {
  const authHeader = req.headers.get('Authorization');
  if (!authHeader) {
    throw new Error('Missing authorization header');
  }

  const token = authHeader.replace('Bearer ', '');
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_ANON_KEY') ?? '',
  );

  const { data: { user }, error } = await supabase.auth.getUser(token);
  
  if (error || !user) {
    throw new Error('Invalid authorization token');
  }

  return user;
};

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

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders
    });
  }

  try {
    if (req.method !== 'POST') {
      throw new Error('Method not allowed');
    }

    // Verify authentication
    const user = await verifyAuth(req);

    const { recursionCount, cocoonTrace, lastStableTimestamp, fallbackState }: FallbackRequest = await req.json();

    if (!Array.isArray(cocoonTrace)) {
      throw new Error('Invalid cocoonTrace format');
    }

    const recoverySuggestions = getRecoverySuggestions(cocoonTrace);
    const failureCount = cocoonTrace.filter(entry => 
      entry.toLowerCase().includes('failed') || 
      entry.toLowerCase().includes('error')
    ).length;

    const confidence = calculateConfidence(
      100, // Initial cooldown
      failureCount,
      'Online' // Default to online, edge function is running
    );

    const summary = `Fallback mode is active. Recursion count is ${recursionCount}. Confidence level is ${confidence.status}. ` +
      (recoverySuggestions.length > 0 ? `Suggested actions include: ${recoverySuggestions.join(', ')}.` : 'No recovery suggestions available.');

    const response = {
      summary,
      confidence,
      timestamp: new Date().toISOString(),
      suggestions: recoverySuggestions,
      metrics: {
        recursionCount,
        failureCount,
        lastStableTimestamp,
        fallbackState,
        userId: user.id
      }
    };

    return new Response(
      JSON.stringify(response),
      { 
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      }
    );

  } catch (error) {
    console.error('Error processing fallback request:', error);

    const status = 
      error.message === 'Method not allowed' ? 405 :
      error.message === 'Missing authorization header' ? 401 :
      error.message === 'Invalid authorization token' ? 403 :
      500;

    return new Response(
      JSON.stringify({
        error: error.message || 'Internal server error',
        timestamp: new Date().toISOString()
      }),
      { 
        status,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      }
    );
  }
});