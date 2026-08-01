/*
  # Create storage bucket for Codette files

  1. New Storage Bucket
    - Creates 'codette-files' bucket for storing uploaded files
  2. Security
    - Enable public access for authenticated users
    - Add policies for read and write operations
*/

-- Create the storage bucket
INSERT INTO storage.buckets (id, name)
VALUES ('codette-files', 'codette-files')
ON CONFLICT (id) DO NOTHING;

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