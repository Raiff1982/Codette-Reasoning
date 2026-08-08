/*
  # Update RLS policies for file management

  1. Changes
    - Update storage.objects policies
    - Update codette_files table policies
    
  2. Security
    - Allow authenticated users to read files
    - Allow admin users to upload files
    - Allow admin users to insert file records
*/

BEGIN;

-- Drop existing policies if they exist
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

COMMIT;