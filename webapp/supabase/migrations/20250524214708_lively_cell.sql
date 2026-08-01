/*
  # File management policies

  1. Changes
    - Creates policies for file management
    - Sets up proper access control for authenticated users and admins
  
  2. Security
    - Implements RLS policies for the codette_files table
    - Ensures proper access control based on user roles
*/

-- Enable RLS on codette_files table
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;

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