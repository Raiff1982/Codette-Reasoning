import { useState, useEffect } from 'react';
import { supabase, getSession, clearSession } from '@/lib/supabase';

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  user: any | null;
  role: string | null;
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    error: null,
    user: null,
    role: null
  });

  const signIn = async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
      });

      if (error) throw error;

      if (data.user) {
        const { data: roleData, error: roleError } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', data.user.id)
          .single();

        setAuthState({
          isAuthenticated: true,
          isLoading: false,
          error: null,
          user: data.user,
          role: roleData?.role || null
        });
      }
    } catch (error: any) {
      console.error('Sign in error:', error);
      setAuthState(prev => ({
        ...prev,
        error: error.message,
        isLoading: false
      }));
      throw error;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      try {
        const session = await getSession();
        
        if (!session?.user) {
          setAuthState({
            isAuthenticated: false,
            isLoading: false,
            error: null,
            user: null,
            role: null
          });
          return;
        }

        const { data: roleData, error: roleError } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', session.user.id)
          .single();

        setAuthState({
          isAuthenticated: true,
          isLoading: false,
          error: null,
          user: session.user,
          role: roleData?.role || null
        });
      } catch (error: any) {
        console.error('Auth initialization error:', error);
        setAuthState({
          isAuthenticated: false,
          isLoading: false,
          error: error.message,
          user: null,
          role: null
        });
      }
    };

    initAuth();

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_OUT') {
        clearSession();
        setAuthState({
          isAuthenticated: false,
          isLoading: false,
          error: null,
          user: null,
          role: null
        });
        return;
      }

      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        if (!session?.user) {
          setAuthState(prev => ({ ...prev, error: 'No user in session' }));
          return;
        }

        try {
          const { data: roleData, error: roleError } = await supabase
            .from('user_roles')
            .select('role')
            .eq('user_id', session.user.id)
            .single();

          setAuthState({
            isAuthenticated: true,
            isLoading: false,
            error: null,
            user: session.user,
            role: roleData?.role || null
          });
        } catch (error: any) {
          console.error('Error fetching user role:', error);
          setAuthState(prev => ({
            ...prev,
            error: error.message,
            role: null
          }));
        }
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  const signOut = async () => {
    try {
      await supabase.auth.signOut();
      clearSession();
    } catch (error: any) {
      console.error('Sign out error:', error);
      setAuthState(prev => ({ ...prev, error: error.message }));
    }
  };

  return {
    ...authState,
    signIn,
    signOut
  };
}