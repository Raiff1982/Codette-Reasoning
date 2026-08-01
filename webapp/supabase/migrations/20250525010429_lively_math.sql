/*
  # Update storage policies for codette-files

  This migration updates the storage policies for the codette-files bucket,
  ensuring proper access control for authenticated users and admins.

  1. Changes
    - Drop existing policies to avoid conflicts
    - Create new policies for file access and upload
*/

-- First check if policies exist and drop them if they do
DO $$
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Allow authenticated users to read files" ON storage.objects;
    DROP POLICY IF EXISTS "Allow admin users to upload files" ON storage.objects;
    DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;
END $$;

-- Create new policies
DO $$
BEGIN
    -- Create policy to allow authenticated users to read any file
    CREATE POLICY "Allow authenticated users to read files 2"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'codette-files');

    -- Create policy to allow only admin users to upload files
    CREATE POLICY "Allow admin users to upload files 2"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'codette-files' AND (auth.jwt() ->> 'role')::text = 'admin');

    -- Update the codette_files table policies
    CREATE POLICY "Allow admin users to insert files 2"
    ON public.codette_files FOR INSERT
    TO authenticated
    WITH CHECK ((auth.jwt() ->> 'role')::text = 'admin');
END $$;