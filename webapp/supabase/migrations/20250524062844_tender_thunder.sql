/*
  # Update codette_files table and policies

  1. New Tables
    - Ensures codette_files table exists with proper structure
      - id (uuid, primary key)
      - filename (text)
      - storage_path (text)
      - file_type (text, nullable)
      - uploaded_at (timestamptz)
      - created_at (timestamptz)

  2. Security
    - Enables RLS if not already enabled
    - Adds admin-specific policies for file management
*/

-- Create table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.codette_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text NOT NULL,
  file_type text,
  uploaded_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security (idempotent operation)
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow authenticated users to insert files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow admin users to manage files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;

-- Create new policies
CREATE POLICY "Allow authenticated users to read files"
  ON public.codette_files
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Allow authenticated users to insert files"
  ON public.codette_files
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Add admin-specific policies
CREATE POLICY "Allow admin users to manage files"
  ON public.codette_files
  FOR ALL
  TO authenticated
  USING ((auth.jwt() ->> 'role'::text) = 'admin'::text)
  WITH CHECK ((auth.jwt() ->> 'role'::text) = 'admin'::text);

CREATE POLICY "Allow admin users to insert files"
  ON public.codette_files
  FOR INSERT
  TO authenticated
  WITH CHECK ((auth.jwt() ->> 'role'::text) = 'admin'::text);