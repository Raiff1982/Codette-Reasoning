/*
  # File management and storage setup

  1. Changes
    - Enables RLS on codette_files table
    - Creates necessary policies for file management
  
  2. Security
    - Implements proper access control through RLS
    - Sets up role-based permissions
*/

-- Enable RLS on codette_files table if not already enabled
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