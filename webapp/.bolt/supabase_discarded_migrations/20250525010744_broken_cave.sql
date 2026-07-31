/*
  # Database Schema Cleanup and Setup

  1. Tables
    - Create codette_files table for storing file metadata
    - Create user_roles table for managing user permissions
  
  2. Storage
    - Create storage bucket for files
    - Set up storage policies
  
  3. Security
    - Enable RLS on tables
    - Create policies for file access and management
    - Set up user roles and permissions
*/

-- Create tables
CREATE TABLE IF NOT EXISTS public.codette_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text NOT NULL,
  file_type text,
  uploaded_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  role text NOT NULL CHECK (role IN ('admin', 'user')),
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Create storage bucket
DO $$
BEGIN
  INSERT INTO storage.buckets (id, name)
  VALUES ('codette-files', 'codette-files')
  ON CONFLICT (id) DO NOTHING;
END $$;

-- Create policies for user_roles
DO $$
BEGIN
  CREATE POLICY "Users can read own role"
    ON public.user_roles
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

  CREATE POLICY "Admin users can manage roles"
    ON public.user_roles
    FOR ALL
    TO authenticated
    USING (
      EXISTS (
        SELECT 1 FROM public.user_roles
        WHERE user_id = auth.uid()
        AND role = 'admin'
      )
    );
END $$;

-- Create policies for codette_files
DO $$
BEGIN
  CREATE POLICY "Allow authenticated users to read codette_files"
    ON public.codette_files
    FOR SELECT
    TO authenticated
    USING (true);

  CREATE POLICY "Allow admin users to insert codette_files"
    ON public.codette_files
    FOR INSERT
    TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1 FROM public.user_roles
        WHERE user_id = auth.uid()
        AND role = 'admin'
      )
    );
END $$;

-- Create function to get user role
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN (
    SELECT role
    FROM public.user_roles
    WHERE user_id = auth.uid()
    LIMIT 1
  );
END;
$$;

-- Create initial admin user
DO $$
DECLARE
  admin_user_id uuid;
BEGIN
  -- Create admin user if not exists
  INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at
  )
  VALUES (
    '00000000-0000-0000-0000-000000000000',
    gen_random_uuid(),
    'authenticated',
    'authenticated',
    'admin@codette.ai',
    crypt('admin123', gen_salt('bf')),
    now(),
    now(),
    now()
  )
  ON CONFLICT (email) DO NOTHING
  RETURNING id INTO admin_user_id;

  -- Get the user ID if the insert didn't happen
  IF admin_user_id IS NULL THEN
    SELECT id INTO admin_user_id FROM auth.users WHERE email = 'admin@codette.ai';
  END IF;

  -- Add admin role
  INSERT INTO public.user_roles (user_id, role)
  VALUES (admin_user_id, 'admin')
  ON CONFLICT (user_id) DO NOTHING;
END $$;