/*
  # Setup codette_files table and RLS

  This migration sets up the codette_files table with proper RLS and policies.
  It avoids modifying storage.objects directly since we don't have sufficient permissions.

  1. Changes
    - Enable RLS on codette_files table
    - Create policies for authenticated users
*/

-- Enable RLS on the codette_files table
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;

-- Create policies for the codette_files table
DO $$
BEGIN
    -- Create policy for reading files
    CREATE POLICY "Allow authenticated users to read codette_files"
    ON public.codette_files FOR SELECT
    TO authenticated
    USING (true);

    -- Create policy for admin file insertion
    CREATE POLICY "Allow admin users to insert codette_files"
    ON public.codette_files FOR INSERT
    TO authenticated
    WITH CHECK ((auth.jwt() ->> 'role')::text = 'admin');
END $$;