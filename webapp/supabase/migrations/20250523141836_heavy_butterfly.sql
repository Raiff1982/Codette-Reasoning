/*
  # Storage and RLS Policy Setup

  1. Changes
    - Create storage bucket policies for file access
    - Create table policies for file management
    - Enable RLS on codette_files table
  
  2. Security
    - Authenticated users can read files
    - Admin users can upload files
    - RLS enabled on codette_files table
*/

-- Create storage bucket if it doesn't exist
DO $$
BEGIN
    INSERT INTO storage.buckets (id, name)
    VALUES ('codette-files', 'codette-files')
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Storage Policies
DO $$
BEGIN
    -- Drop existing policies to avoid conflicts
    DROP POLICY IF EXISTS "Allow authenticated users to read files" ON storage.objects;
    DROP POLICY IF EXISTS "Allow admin users to upload files" ON storage.objects;
    
    -- Create new storage policies
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
END $$;

-- File Management Table Policies
DO $$
BEGIN
    -- Drop existing policies to avoid conflicts
    DROP POLICY IF EXISTS "Allow authenticated users to read files" ON public.codette_files;
    DROP POLICY IF EXISTS "Allow admin users to insert files" ON public.codette_files;
    DROP POLICY IF EXISTS "Allow authenticated users to insert files" ON public.codette_files;
    
    -- Create new table policies
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
END $$;

-- Enable RLS
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;