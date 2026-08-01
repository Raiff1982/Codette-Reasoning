/*
  # Update storage policies with existence checks
  
  1. Changes
    - Add existence checks before creating each policy
    - Only create policies that don't already exist
    - Maintain all required policies for the storage bucket
  
  2. Security
    - Maintain existing RLS policies
    - Ensure proper access control for authenticated users
    - Preserve admin-only upload restrictions
*/

-- Wrap everything in a transaction
BEGIN;

-- Create policies with existence checks
DO $$
BEGIN
    -- Check and create read policy
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND schemaname = 'storage'
        AND policyname = 'Allow authenticated users to read files'
    ) THEN
        CREATE POLICY "Allow authenticated users to read files"
        ON storage.objects FOR SELECT
        TO authenticated
        USING (bucket_id = 'codette-files');
    END IF;

    -- Check and create upload policy for admin users
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND schemaname = 'storage'
        AND policyname = 'Allow admin users to upload files'
    ) THEN
        CREATE POLICY "Allow admin users to upload files"
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (bucket_id = 'codette-files' AND auth.jwt() ->> 'role' = 'admin');
    END IF;

    -- Check and create policy for admin file insertion
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'codette_files' 
        AND schemaname = 'public'
        AND policyname = 'Allow admin users to insert files'
    ) THEN
        CREATE POLICY "Allow admin users to insert files"
        ON public.codette_files FOR INSERT
        TO authenticated
        WITH CHECK (auth.jwt() ->> 'role' = 'admin');
    END IF;
END $$;

COMMIT;