import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { decode as decodeJwt } from 'https://deno.land/x/djwt@v2.8/mod.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, cache-control, pragma',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Max-Age': '86400',
  'Vary': 'Origin'
};

const getEnvConfig = () => {
  const config = {
    KAGGLE_API_KEY: Deno.env.get('KAGGLE_API_KEY'),
    KAGGLE_MODEL_ENDPOINT: Deno.env.get('KAGGLE_MODEL_ENDPOINT'),
    SUPABASE_SERVICE_ROLE_KEY: Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'),
    SUPABASE_ANON_KEY: Deno.env.get('SUPABASE_ANON_KEY'),
  };

  const missingVars = Object.entries(config)
    .filter(([_, value]) => !value)
    .map(([key]) => key);

  if (missingVars.length > 0) {
    console.error(`Missing environment variables: ${missingVars.join(', ')}`);
    return {
      error: true,
      message: `Missing required environment variables: ${missingVars.join(', ')}`,
      config: null
    };
  }

  try {
    new URL(config.KAGGLE_MODEL_ENDPOINT);
  } catch (error) {
    console.error('Invalid KAGGLE_MODEL_ENDPOINT URL format');
    return {
      error: true,
      message: 'Invalid KAGGLE_MODEL_ENDPOINT URL format',
      config: null
    };
  }

  return {
    error: false,
    message: null,
    config
  };
};

const verifyAuth = async (req: Request) => {
  const authHeader = req.headers.get('Authorization');
  const apiKey = req.headers.get('apikey');

  if (!authHeader && !apiKey) {
    return { error: 'Missing authorization header and API key' };
  }

  const configResult = getEnvConfig();
  if (configResult.error || !configResult.config) {
    return { error: 'Server configuration error' };
  }

  // Check if using service role key
  const token = authHeader?.replace('Bearer ', '');
  if (token === configResult.config.SUPABASE_SERVICE_ROLE_KEY) {
    return { error: null };
  }

  // Check if using anon key
  if (apiKey === configResult.config.SUPABASE_ANON_KEY) {
    return { error: null };
  }

  // If not using service role or anon key, verify JWT
  if (token) {
    try {
      const [header, payload] = await decodeJwt(token);
      
      if (!header || !payload) {
        return { error: 'Invalid JWT format' };
      }

      // Check if token is expired
      const exp = payload.exp;
      if (exp && Date.now() >= exp * 1000) {
        return { error: 'Token has expired' };
      }

      return { error: null };
    } catch (error) {
      console.error('JWT verification error:', error);
      return { error: 'Invalid authorization token' };
    }
  }

  return { error: 'Invalid authentication credentials' };
};

const handleHealthCheck = async (req: Request) => {
  console.log('Processing health check request');
  
  const authResult = await verifyAuth(req);
  if (authResult.error) {
    return new Response(
      JSON.stringify({ 
        status: 'error',
        message: authResult.error,
        timestamp: new Date().toISOString()
      }),
      { 
        status: 401,
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders 
        }
      }
    );
  }
  
  const configResult = getEnvConfig();
  
  if (configResult.error) {
    console.error('Configuration error:', configResult.message);
    return new Response(
      JSON.stringify({ 
        status: 'error',
        message: configResult.message,
        timestamp: new Date().toISOString()
      }),
      { 
        status: 503,
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders 
        }
      }
    );
  }

  try {
    console.log('Testing Kaggle API connection...');
    
    const testResponse = await fetch(configResult.config.KAGGLE_MODEL_ENDPOINT, {
      method: 'HEAD',
      headers: {
        'Authorization': `Bearer ${configResult.config.KAGGLE_API_KEY}`,
        'Content-Type': 'application/json'
      }
    }).catch(error => {
      console.error('Network error during health check:', error);
      throw new Error(`Network error: ${error.message}`);
    });

    if (!testResponse.ok) {
      const errorMessage = `Kaggle API returned status ${testResponse.status}`;
      console.error(errorMessage);
      throw new Error(errorMessage);
    }

    console.log('Health check successful');
    return new Response(
      JSON.stringify({ 
        status: 'healthy',
        message: 'Service is operational',
        timestamp: new Date().toISOString()
      }),
      { 
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders 
        }
      }
    );
  } catch (error) {
    console.error('Health check failed:', error);
    
    return new Response(
      JSON.stringify({ 
        status: 'error',
        message: error.message || 'Unknown error during health check',
        timestamp: new Date().toISOString(),
        details: error.stack
      }),
      { 
        status: 503,
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders 
        }
      }
    );
  }
};

serve(async (req) => {
  try {
    console.log(`Received ${req.method} request to ${new URL(req.url).pathname}`);

    if (req.method === 'OPTIONS') {
      return new Response(null, { 
        status: 204,
        headers: corsHeaders
      });
    }

    const authResult = await verifyAuth(req);
    if (authResult.error) {
      return new Response(
        JSON.stringify({ 
          success: false,
          error: authResult.error,
          timestamp: new Date().toISOString()
        }),
        { 
          status: 401,
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders 
          }
        }
      );
    }

    const url = new URL(req.url);
    if (url.pathname.endsWith('/health')) {
      return await handleHealthCheck(req);
    }

    const configResult = getEnvConfig();
    
    if (configResult.error) {
      console.error('Configuration error:', configResult.message);
      return new Response(
        JSON.stringify({ 
          success: false, 
          error: configResult.message,
          timestamp: new Date().toISOString()
        }),
        { 
          status: 503,
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders 
          }
        }
      );
    }

    if (req.method !== 'POST') {
      return new Response(
        JSON.stringify({ 
          success: false, 
          error: 'Method not allowed' 
        }),
        { 
          status: 405,
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders,
            'Allow': 'POST, OPTIONS'
          }
        }
      );
    }

    let requestData;
    try {
      requestData = await req.json();
    } catch (error) {
      console.error('Invalid JSON in request body:', error);
      return new Response(
        JSON.stringify({
          success: false,
          error: 'Invalid JSON in request body',
          details: error.message
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        }
      );
    }
    
    if (!requestData.prompt) {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'Missing prompt in request body'
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        }
      );
    }

    try {
      console.log('Sending request to Kaggle API...');
      const response = await fetch(configResult.config.KAGGLE_MODEL_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${configResult.config.KAGGLE_API_KEY}`,
        },
        body: JSON.stringify({ prompt: requestData.prompt })
      }).catch(error => {
        console.error('Network error during Kaggle API request:', error);
        throw new Error(`Network error: ${error.message}`);
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'No error details available');
        console.error('Kaggle API error:', response.status, errorText);
        throw new Error(`Kaggle API error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log('Successfully received response from Kaggle API');

      return new Response(
        JSON.stringify({ 
          success: true, 
          response: data.response || data,
          timestamp: new Date().toISOString()
        }),
        { 
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders 
          } 
        }
      );
    } catch (error) {
      console.error('Error processing request:', error);
      return new Response(
        JSON.stringify({ 
          success: false, 
          error: error.message || 'An unknown error occurred',
          timestamp: new Date().toISOString(),
          details: error.stack
        }),
        { 
          status: 500,
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders 
          }
        }
      );
    }
  } catch (error) {
    console.error('Error processing request:', error);
    return new Response(
      JSON.stringify({ 
        success: false, 
        error: error.message || 'An unknown error occurred',
        timestamp: new Date().toISOString(),
        details: error.stack
      }),
      { 
        status: error.message?.includes('environment variables') ? 503 
          : error.message?.includes('Invalid JSON') ? 400 
          : error.message?.includes('Missing prompt') ? 400 
          : 500,
        headers: { 
          'Content-Type': 'application/json',
          ...corsHeaders 
        }
      }
    );
  }
});