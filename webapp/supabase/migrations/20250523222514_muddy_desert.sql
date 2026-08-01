/*
  # Storage bucket and RLS policies

  1. Changes
    - Create storage bucket for Codette files
    - Set up RLS policies for the bucket
    
  2. Security
    - Enable RLS policies for storage bucket
    - Allow authenticated users to read files
    - Allow authenticated users to upload files
    - Allow authenticated users to update files
    - Allow authenticated users to delete files
*/

-- Create the storage bucket
INSERT INTO storage.buckets (id, name)
VALUES ('codette-files', 'codette-files')
ON CONFLICT (id) DO NOTHING;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow authenticated users to read files" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to upload files" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to update files" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated users to delete files" ON storage.objects;

-- Set up RLS policies for the bucket
CREATE POLICY "Allow authenticated users to read files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'codette-files');

CREATE POLICY "Allow authenticated users to upload files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'codette-files');

CREATE POLICY "Allow authenticated users to update files"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'codette-files')
WITH CHECK (bucket_id = 'codette-files');

CREATE POLICY "Allow authenticated users to delete files"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'codette-files');