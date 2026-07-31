/*
  # Storage and File Management Setup

  1. New Storage Configuration
    - Creates 'codette-files' storage bucket if it doesn't exist
    - Sets up proper file management structure

  2. Table Policies
    - Enables RLS on codette_files table
    - Creates read policy for authenticated users
    - Creates insert policies for both admin and authenticated users
    - Ensures proper access control and security

  Note: Storage object policies must be created manually through Supabase dashboard
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
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('codette-files', 'codette-files', false);
    END IF;
END $$;

-- Create policies for the codette_files table
DO $$
BEGIN
    -- Create read policy if it doesn't exist
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

    -- Create admin insert policy if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE policyname = 'Allow admin users to insert files'
        AND tablename = 'codette_files'
    ) THEN
        CREATE POLICY "Allow admin users to insert files"
        ON public.codette_files FOR INSERT
        TO authenticated
        WITH CHECK ((auth.jwt() ->> 'role')::text = 'admin');
    END IF;

    -- Create authenticated insert policy if it doesn't exist
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

-- Important: Storage object policies must be created manually through the Supabase dashboard
-- Create the following policies:
-- 1. "Allow authenticated users to read files"
--    - Operation: SELECT
--    - Target roles: authenticated
--    - Using expression: bucket_id = 'codette-files'
--
-- 2. "Allow admin users to upload files"
--    - Operation: INSERT
--    - Target roles: authenticated
--    - Using expression: bucket_id = 'codette-files' AND (auth.jwt() ->> 'role')::text = 'admin'