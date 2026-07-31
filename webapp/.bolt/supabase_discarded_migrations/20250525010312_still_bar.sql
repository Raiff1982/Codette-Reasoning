/*
  # Update storage policies for codette-files

  1. Changes
    - Add policies for storage.objects table for codette-files bucket
    - Add policies for codette_files table
  
  2. Security
    - Allow authenticated users to read files
    - Restrict file uploads to admin users only
    - Ensure admin-only access for file management
*/

DO $$ 
BEGIN
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
  USING (bucket_id = 'codette-files' AND auth.jwt() ->> 'role' = 'admin');

  -- Update the codette_files table policies
  CREATE POLICY "Allow admin users to insert files"
  ON public.codette_files FOR INSERT
  TO authenticated
  WITH CHECK (auth.jwt() ->> 'role' = 'admin');
END $$;