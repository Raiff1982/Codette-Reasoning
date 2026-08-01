/*
  # Set up admin authentication

  1. Changes
    - Create admin role
    - Set up auth schema and tables
    - Create admin user with proper credentials
    - Enable RLS and policies

  2. Security
    - Enable RLS on auth tables
    - Add policies for admin access
*/

-- Create auth schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS auth;

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS auth.users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  encrypted_password text NOT NULL,
  role text DEFAULT 'user',
  email_confirmed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- Create policy for admin users
CREATE POLICY "Allow admin users full access"
ON auth.users
FOR ALL
TO authenticated
USING (
  (auth.jwt() ->> 'role'::text) = 'admin'::text
)
WITH CHECK (
  (auth.jwt() ->> 'role'::text) = 'admin'::text
);

-- Create admin user if not exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM auth.users 
    WHERE email = 'admin@codette.ai'
  ) THEN
    INSERT INTO auth.users (
      email,
      encrypted_password,
      role,
      email_confirmed_at
    )
    VALUES (
      'admin@codette.ai',
      crypt('admin123', gen_salt('bf')),
      'admin',
      now()
    );
  END IF;
END
$$;