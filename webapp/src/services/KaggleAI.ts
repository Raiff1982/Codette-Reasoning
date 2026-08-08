import { getSupabaseHeaders, verifySession } from '@/lib/supabase';
import fetch from 'cross-fetch';
import retry from 'retry';

export class KaggleAI {
  private supabaseUrl: string;
  private fallbackMode: boolean = false;
  private retryCount: number = 3;
  private retryDelay: number = 1000;
  private maxRetryDelay: number = 15000;
  private initialized: boolean = false;
  private initializationError: string | null = null;
  private lastFailureTime: number = 0;
  private failureCount: number = 0;
  private readonly maxFailures: number = 3;
  private readonly circuitBreakerTimeout: number = 180000;
  private lastHealthCheck: number = 0;
  private readonly healthCheckInterval: number = 30000;
  private cache: Map<string, { response: string; timestamp: number }> = new Map();
  private readonly cacheExpiration: number = 3600000;
  private readonly requestTimeout: number = 30000;
  private authRetryCount: number = 0;
  private readonly maxAuthRetries: number = 5;
  private readonly authRetryDelay = (attempt: number) => Math.min(2000 * Math.pow(2, attempt), 30000);

  constructor() {
    this.supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';

    if (!this.supabaseUrl) {
      console.error('Missing Supabase URL');
      this.fallbackMode = true;
      this.initializationError = 'Supabase configuration missing. Check your environment variables.';
      return;
    }

    try {
      new URL(this.supabaseUrl);
    } catch (e) {
      console.error('Invalid Supabase URL format:', e);
      this.fallbackMode = true;
      this.initializationError = 'Invalid Supabase URL format. Please check your configuration.';
    }
  }

  private async getHeaders(): Promise<Record<string, string>> {
    try {
      const headers = await getSupabaseHeaders();
      if (!headers.Authorization) {
        throw new Error('No authorization header found');
      }
      return {
        ...headers,
        'Content-Type': 'application/json'
      };
    } catch (error) {
      console.error('Failed to get headers:', error);
      this.fallbackMode = true;
      throw error;
    }
  }

  private async checkHealth(): Promise<boolean> {
    console.log('Performing health check...');
    const now = Date.now();
    if (now - this.lastHealthCheck < this.healthCheckInterval) {
      return !this.fallbackMode;
    }

    this.lastHealthCheck = now;

    try {
      const headers = await this.getHeaders();
      const operation = retry.operation({
        retries: 2,
        factor: 2,
        minTimeout: 1000,
        maxTimeout: 5000,
        randomize: true
      });

      return await new Promise<boolean>((resolve, reject) => {
        operation.attempt(async (currentAttempt) => {
          console.log(`Health check attempt ${currentAttempt}`);
          try {
            const response = await fetch(`${this.supabaseUrl}/functions/v1/kaggle-proxy/health`, {
              method: 'GET',
              headers,
              signal: AbortSignal.timeout(10000)
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({ error: 'No error details available' }));
              throw new Error(`Health check failed with status ${response.status}: ${JSON.stringify(errorData)}`);
            }

            const data = await response.json();
            const isHealthy = data.status === 'healthy';
            
            if (isHealthy && this.fallbackMode) {
              console.log('Service recovered, disabling fallback mode');
              this.fallbackMode = false;
              this.failureCount = 0;
            }

            resolve(isHealthy);
          } catch (error: any) {
            console.error('Health check error:', error);
            
            if (error.name === 'AbortError') {
              reject(new Error('Health check timed out'));
              return;
            }

            if (operation.retry(error)) {
              return;
            }
            reject(operation.mainError());
          }
        });
      });
    } catch (error) {
      console.error('Health check failed completely:', error);
      return false;
    }
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;
    if (this.initializationError) throw new Error(this.initializationError);
    
    const initializeWithRetry = async (attempt = 0): Promise<void> => {
      try {
        console.log(`Initializing KaggleAI service (attempt ${attempt + 1}/${this.maxAuthRetries})...`);
        const isAuthenticated = await verifySession();
        
        if (!isAuthenticated) {
          if (attempt < this.maxAuthRetries) {
            console.log('Authentication failed, implementing exponential backoff...');
            await new Promise(resolve => setTimeout(resolve, this.authRetryDelay(attempt)));
            return initializeWithRetry(attempt + 1);
          }
          throw new Error('User not authenticated after maximum retries');
        }
        
        this.initialized = true;
        this.initializationError = null;
        this.failureCount = 0;
        this.authRetryCount = 0;
        console.log('KaggleAI initialized successfully');
      } catch (error: any) {
        console.error('Failed to initialize KaggleAI:', error);
        
        if (error.message?.includes('captcha')) {
          if (attempt < this.maxAuthRetries) {
            console.log('CAPTCHA error, implementing exponential backoff...');
            await new Promise(resolve => setTimeout(resolve, this.authRetryDelay(attempt)));
            return initializeWithRetry(attempt + 1);
          }
        }
        
        this.fallbackMode = true;
        this.initializationError = error.message;
        this.recordFailure();
        throw error;
      }
    };

    await initializeWithRetry();
  }

  private async fetchWithRetry(url: string, options: RequestInit): Promise<Response> {
    if (this.isCircuitBreakerOpen()) {
      throw new Error('Service temporarily unavailable due to multiple failures. Please try again later.');
    }

    const operation = retry.operation({
      retries: this.retryCount,
      factor: 2,
      minTimeout: this.retryDelay,
      maxTimeout: this.maxRetryDelay,
      randomize: true
    });

    return new Promise((resolve, reject) => {
      operation.attempt(async (currentAttempt) => {
        try {
          console.log(`Attempt ${currentAttempt} to fetch from Kaggle API:`, {
            url,
            method: options.method
          });

          const headers = await this.getHeaders();
          const response = await fetch(url, {
            ...options,
            headers: { ...headers, ...options.headers },
            signal: AbortSignal.timeout(this.requestTimeout)
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'No error details available' }));
            throw new Error(`HTTP error! status: ${response.status}, details: ${JSON.stringify(errorData)}`);
          }
          
          this.failureCount = 0;
          resolve(response);
        } catch (error: any) {
          console.error('Fetch error:', error);

          if (error.name === 'AbortError') {
            this.recordFailure();
            reject(new Error(`Request timed out after ${this.requestTimeout / 1000} seconds`));
            return;
          }

          if (operation.retry(error)) {
            return;
          }
          
          this.recordFailure();
          reject(operation.mainError());
        }
      });
    });
  }

  async generateResponse(prompt: string): Promise<string> {
    if (!this.initialized && !this.fallbackMode) {
      await this.initialize().catch(() => {
        this.fallbackMode = true;
      });
    }

    if (this.fallbackMode || this.isCircuitBreakerOpen()) {
      return this.getFallbackResponse(prompt);
    }

    try {
      const cachedResponse = this.getCachedResponse(prompt);
      if (cachedResponse) {
        return cachedResponse;
      }

      const isAuthenticated = await verifySession();
      if (!isAuthenticated) {
        throw new Error('User not authenticated');
      }

      const response = await this.fetchWithRetry(`${this.supabaseUrl}/functions/v1/kaggle-proxy`, {
        method: 'POST',
        body: JSON.stringify({ prompt })
      });

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to generate response');
      }

      const result = data.response || 'No response received from the model.';
      this.setCachedResponse(prompt, result);
      return result;
    } catch (error: any) {
      console.error('Error generating response:', error);
      this.fallbackMode = true;
      return this.getFallbackResponse(prompt);
    }
  }

  private getFallbackResponse(prompt: string): string {
    if (this.isCircuitBreakerOpen()) {
      return `Service is temporarily unavailable due to multiple failures. Please try again after ${Math.ceil(this.circuitBreakerTimeout / 60000)} minutes.`;
    }
    
    if (this.initializationError?.includes('configuration')) {
      return 'AI service configuration error. Please check your environment variables.';
    }
    
    return `Operating in fallback mode due to connectivity issues (as of ${new Date().toLocaleTimeString()}). You asked about: "${prompt}"`;
  }

  private getCachedResponse(prompt: string): string | null {
    const cached = this.cache.get(prompt);
    if (cached && Date.now() - cached.timestamp < this.cacheExpiration) {
      return cached.response;
    }
    return null;
  }

  private setCachedResponse(prompt: string, response: string) {
    this.cache.set(prompt, {
      response,
      timestamp: Date.now()
    });
  }

  private recordFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    console.log(`Failure recorded. Current count: ${this.failureCount}`);
  }

  private isCircuitBreakerOpen(): boolean {
    if (this.failureCount >= this.maxFailures) {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      if (timeSinceLastFailure < this.circuitBreakerTimeout) {
        return true;
      }
      this.failureCount = 0;
    }
    return false;
  }
}

export default KaggleAI;