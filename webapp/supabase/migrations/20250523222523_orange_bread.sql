/*
  # Update RLS policies for file management

  1. Changes
    - Update storage.objects policies
    - Update codette_files table policies
    - Enable RLS on codette_files table
    
  2. Security
    - Allow authenticated users to read files
    - Allow admin users to upload files
    - Allow authenticated users to insert files
*/

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON storage.objects;
DROP POLICY IF EXISTS "Allow admin users to upload files" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;
DROP POLICY IF EXISTS "Allow authenticated users to insert files" ON public.codette_files;

-- Storage Policies
CREATE POLICY "Allow authenticated users to read files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'codette-files');

CREATE POLICY "Allow admin users to upload files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'codette-files' 
    AND (auth.jwt() ->> 'role' = 'admin')
);

-- File Management Policies
CREATE POLICY "Allow authenticated users to read files"
ON public.codette_files FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Allow admin users to insert files"
ON public.codette_files FOR INSERT
TO authenticated
WITH CHECK (auth.jwt() ->> 'role' = 'admin');

CREATE POLICY "Allow authenticated users to insert files"
ON public.codette_files FOR INSERT
TO authenticated
WITH CHECK (true);

-- Enable RLS
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;