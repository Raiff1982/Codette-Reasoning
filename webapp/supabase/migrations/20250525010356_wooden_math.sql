/*
  # Enable RLS and setup codette_files policies

  1. Changes
    - Enable RLS on codette_files table
    - Create policies for authenticated users to read files
    - Create policies for admin users to insert files
    - Remove storage.objects policies (handled by Supabase)

  2. Security
    - Maintain RLS for all tables
    - Ensure proper access control for files
*/

-- First, enable RLS on the codette_files table if not already enabled
DO $$
BEGIN
    -- Check if RLS is already enabled
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'codette_files' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;
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
END $$;