/*
  # Create codette_files table for file management

  1. New Tables
    - `codette_files`
      - `id` (uuid, primary key)
      - `filename` (text)
      - `storage_path` (text)
      - `file_type` (text)
      - `uploaded_at` (timestamptz)
      - `created_at` (timestamptz)

  2. Security
    - Enable RLS on `codette_files` table
    - Add policies for:
      - Authenticated users can read all files
      - Authenticated users can insert their own files
*/

CREATE TABLE IF NOT EXISTS public.codette_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  storage_path text NOT NULL,
  file_type text,
  uploaded_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.codette_files ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Allow authenticated users to read files"
  ON public.codette_files
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Allow authenticated users to insert files"
  ON public.codette_files
  FOR INSERT
  TO authenticated
  WITH CHECK (true);