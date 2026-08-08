/*
  # Fix tables and policies setup

  1. New Tables
    - `codette_files`
      - `id` (uuid, primary key)
      - `filename` (text)
      - `storage_path` (text)
      - `file_type` (text)
      - `uploaded_at` (timestamptz)
      - `created_at` (timestamptz)
    - `user_roles`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references auth.users)
      - `role` (text)
      - `created_at` (timestamptz)

  2. Security
    - Enable RLS on both tables
    - Add policies for file access and role management
*/

-- Create codette_files table
CREATE TABLE IF NOT EXISTS public.codette_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text NOT NULL,
  file_type text,
  uploaded_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Create user_roles table
CREATE TABLE IF NOT EXISTS public.user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  role text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow authenticated users to insert files" ON public.codette_files;
DROP POLICY IF EXISTS "Users can read own role" ON public.user_roles;
DROP POLICY IF EXISTS "Admin users can manage roles" ON public.user_roles;

-- Create policies for codette_files
CREATE POLICY "Allow authenticated users to read files"
ON public.codette_files FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Allow admin users to insert files"
ON public.codette_files FOR INSERT
TO authenticated
WITH CHECK ((
  SELECT role FROM public.user_roles 
  WHERE user_id = auth.uid() 
  LIMIT 1
) = 'admin');

-- Create policies for user_roles
CREATE POLICY "Users can read own role"
ON public.user_roles FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "Admin users can manage roles"
ON public.user_roles FOR ALL
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = auth.uid()
    AND role = 'admin'
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = auth.uid()
    AND role = 'admin'
  )
);

-- Create function to get user role
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TABLE (role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT ur.role
  FROM public.user_roles ur
  WHERE ur.user_id = auth.uid()
  LIMIT 1;
END;
$$;