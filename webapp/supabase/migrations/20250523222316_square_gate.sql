/*
  # Fix RLS policies for codette_files table

  1. Changes
    - Drop existing RLS policies that might be conflicting
    - Add new RLS policies for admin users
      - Allow admin users to insert files
      - Allow admin users to read files
      - Allow admin users to update files
      - Allow admin users to delete files
    - Add RLS policies for regular authenticated users
      - Allow reading files only

  2. Security
    - Ensures only admin users can upload/modify files
    - All authenticated users can read files
    - Proper RLS enforcement for file management
*/

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow admin users to insert files" ON codette_files;
DROP POLICY IF EXISTS "Allow authenticated users to insert files" ON codette_files;
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON codette_files;

-- Create new policies with proper checks
CREATE POLICY "Allow admin users to manage files"
ON codette_files
FOR ALL
TO authenticated
USING (
  (auth.jwt() ->> 'role')::text = 'admin'
)
WITH CHECK (
  (auth.jwt() ->> 'role')::text = 'admin'
);

CREATE POLICY "Allow authenticated users to read files"
ON codette_files
FOR SELECT
TO authenticated
USING (true);

-- Enable RLS if not already enabled
ALTER TABLE codette_files ENABLE ROW LEVEL SECURITY;