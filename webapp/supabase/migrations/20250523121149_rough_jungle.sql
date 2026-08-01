/*
  # Create storage bucket and policies

  1. Changes
    - Create codette-files storage bucket if it doesn't exist
    - Add RLS policies for authenticated users to:
      - Read files
      - Upload files
      - Update files
      - Delete files
    - Add safety checks to prevent policy conflicts
*/

-- Create the storage bucket
INSERT INTO storage.buckets (id, name)
VALUES ('codette-files', 'codette-files')
ON CONFLICT (id) DO NOTHING;

-- Set up RLS policies for the bucket with existence checks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND policyname = 'Allow authenticated users to read files'
    ) THEN
        CREATE POLICY "Allow authenticated users to read files"
        ON storage.objects FOR SELECT
        TO authenticated
        USING (bucket_id = 'codette-files');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND policyname = 'Allow authenticated users to upload files'
    ) THEN
        CREATE POLICY "Allow authenticated users to upload files"
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (bucket_id = 'codette-files');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND policyname = 'Allow authenticated users to update files'
    ) THEN
        CREATE POLICY "Allow authenticated users to update files"
        ON storage.objects FOR UPDATE
        TO authenticated
        USING (bucket_id = 'codette-files')
        WITH CHECK (bucket_id = 'codette-files');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' 
        AND policyname = 'Allow authenticated users to delete files'
    ) THEN
        CREATE POLICY "Allow authenticated users to delete files"
        ON storage.objects FOR DELETE
        TO authenticated
        USING (bucket_id = 'codette-files');
    END IF;
END $$;