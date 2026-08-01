/*
  # Create codette_files table and policies

  1. New Tables
    - `codette_files`
      - `id` (uuid, primary key)
      - `filename` (text)
      - `storage_path` (text)
      - `file_type` (text)
      - `uploaded_at` (timestamptz)
      - `created_at` (timestamptz)

  2. Security
    - Enable RLS on codette_files table
    - Add policies for authenticated users to read files
    - Add policy for admin users to upload files
*/

-- Create the codette_files table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.codette_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text NOT NULL,
  file_type text,
  uploaded_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON storage.objects;
DROP POLICY IF EXISTS "Allow admin users to upload files" ON storage.objects;
DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;

-- Create policy to allow authenticated users to read any file
CREATE POLICY "Allow authenticated users to read files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'codette-files');

-- Create policy to allow only admin users to upload files
CREATE POLICY "Allow admin users to upload files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'codette-files' AND auth.jwt() ->> 'role' = 'admin');

-- Update the codette_files table policies
CREATE POLICY "Allow admin users to insert files"
ON public.codette_files FOR INSERT
TO authenticated
WITH CHECK (auth.jwt() ->> 'role' = 'admin');