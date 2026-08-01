/*
  # Update storage policies for codette-files

  1. Changes
    - Remove duplicate policy creation for storage.objects
    - Keep only admin file upload policy
    - Add codette_files table policy for admin file insertion

  2. Security
    - Maintain RLS policies for authenticated users
    - Ensure admin-only file upload capabilities
*/

BEGIN;

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