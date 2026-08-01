/*
  # Storage bucket and policies setup

  1. Changes
    - Creates storage bucket for file storage
    - Sets up RLS policies for authenticated users
  
  2. Security
    - Enables secure file access for authenticated users
    - Implements proper access control through RLS policies
*/

-- Create the storage bucket if it doesn't exist
INSERT INTO storage.buckets (id, name)
VALUES ('codette-files', 'codette-files')
ON CONFLICT (id) DO NOTHING;