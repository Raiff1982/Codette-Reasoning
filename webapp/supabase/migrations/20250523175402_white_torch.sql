/*
  # Storage and File Access Policies

  1. New Policies
    - Enable RLS on codette_files table
    - Create policies for file access and management
  
  2. Security
    - Allow authenticated users to read files
    - Allow admin users to upload files
    - Allow authenticated users to insert file records
*/

-- Enable RLS on the codette_files table if not already enabled
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'codette_files' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- Create storage bucket if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM storage.buckets WHERE name = 'codette-files'
    ) THEN
        INSERT INTO storage.buckets (id, name)
        VALUES ('codette-files', 'codette-files');
    END IF;
END $$;

-- Create policies for the codette_files table
DO $$
BEGIN
    -- Check if the read policy exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE policyname = 'Allow authenticated users to read files'
        AND tablename = 'codette_files'
    ) THEN
        CREATE POLICY "Allow authenticated users to read files"
        ON public.codette_files FOR SELECT
        TO authenticated
        USING (true);
    END IF;

    -- Check if the admin insert policy exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE policyname = 'Allow admin users to insert files'
        AND tablename = 'codette_files'
    ) THEN
        CREATE POLICY "Allow admin users to insert files"
        ON public.codette_files FOR INSERT
        TO authenticated
        WITH CHECK (auth.jwt() ->> 'role' = 'admin');
    END IF;

    -- Check if the authenticated insert policy exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE policyname = 'Allow authenticated users to insert files'
        AND tablename = 'codette_files'
    ) THEN
        CREATE POLICY "Allow authenticated users to insert files"
        ON public.codette_files FOR INSERT
        TO authenticated
        WITH CHECK (true);
    END IF;
END $$;

-- Note: Storage policies for the storage.objects table need to be created through the Supabase dashboard
-- or using the Supabase CLI, as they require special permissions that aren't available in migrations.
-- Please create the following policies manually:
-- 1. "Allow authenticated users to read files" - For SELECT operations on storage.objects where bucket_id = 'codette-files'
-- 2. "Allow admin users to upload files" - For INSERT operations on storage.objects where bucket_id = 'codette-files' AND auth.jwt() ->> 'role' = 'admin'