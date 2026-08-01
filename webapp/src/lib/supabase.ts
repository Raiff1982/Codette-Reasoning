import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables. Please check your .env file.');
}

try {
  new URL(supabaseUrl);
} catch (e) {
  throw new Error('Invalid Supabase URL format. Please check your configuration.');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    storageKey: 'codette-auth-token'
  }
});

let cachedSession = null;
let lastSessionCheck = 0;
const sessionCheckInterval = 15 * 60 * 1000; // 15 minutes
const backoffDelay = (attempt: number) => Math.min(1000 * Math.pow(2, attempt), 30000);

export const getSession = async () => {
  try {
    const now = Date.now();
    
    if (cachedSession && (now - lastSessionCheck) < sessionCheckInterval) {
      return cachedSession;
    }

    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    
    if (sessionError) {
      if (sessionError.message?.includes('captcha')) {
        console.warn('CAPTCHA verification required for session, clearing cached session');
        clearSession();
        return null;
      }
      console.error('Error getting session:', sessionError);
      return null;
    }

    if (session) {
      cachedSession = session;
      lastSessionCheck = now;
      return session;
    }

    clearSession();
    return null;
  } catch (error: any) {
    console.error('Session error:', error);
    if (error.message?.includes('captcha')) {
      clearSession();
    }
    return null;
  }
};

export const getSupabaseHeaders = async () => {
  const session = await getSession();
  
  const headers = {
    'apikey': supabaseAnonKey,
    'Content-Type': 'application/json'
  };

  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }

  return headers;
};

export const verifySession = async (attempt = 0): Promise<boolean> => {
  try {
    const session = await getSession();
    if (!session) {
      return false;
    }
    
    const { data: { user }, error } = await supabase.auth.getUser();
    
    if (error?.message?.includes('captcha')) {
      clearSession();
      if (attempt < 3) {
        await new Promise(resolve => setTimeout(resolve, backoffDelay(attempt)));
        return verifySession(attempt + 1);
      }
      return false;
    }
    
    return !error && !!user;
  } catch (error: any) {
    console.error('Session verification failed:', error);
    if (error.message?.includes('captcha')) {
      clearSession();
    }
    return false;
  }
};

export const clearSession = () => {
  cachedSession = null;
  lastSessionCheck = 0;
  localStorage.removeItem('codette-auth-token');
};