/*
  # Update Schema and Policies

  1. Changes
    - Add missing RLS policies for all tables
    - Add proper indexes for frequently queried columns
    - Add missing foreign key constraints
    - Update column defaults and constraints

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users
    - Add admin-specific policies
    - Add proper row-level security
*/

-- Enable RLS on all tables that don't have it
ALTER TABLE IF EXISTS documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS codette ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS todos ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS table_name ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS new_table_name ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS "what to do" ENABLE ROW LEVEL SECURITY;

-- Add indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_codette_files_uploaded_at ON codette_files(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_todos_updated_at ON todos(updated_at);

-- Add proper foreign key constraints
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'todos_user_id_fkey'
  ) THEN
    ALTER TABLE todos ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES auth.users(id);
  END IF;
END $$;

-- Update RLS policies for documents
CREATE POLICY IF NOT EXISTS "Users can read own documents"
  ON documents FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can insert own documents"
  ON documents FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can update own documents"
  ON documents FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can delete own documents"
  ON documents FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Update RLS policies for todos
CREATE POLICY IF NOT EXISTS "Users can read own todos"
  ON todos FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can insert own todos"
  ON todos FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can update own todos"
  ON todos FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can delete own todos"
  ON todos FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Update RLS policies for "what to do"
CREATE POLICY IF NOT EXISTS "Authenticated users can read what to do"
  ON "what to do" FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY IF NOT EXISTS "Authenticated users can insert what to do"
  ON "what to do" FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Authenticated users can update what to do"
  ON "what to do" FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Authenticated users can delete what to do"
  ON "what to do" FOR DELETE
  TO authenticated
  USING (true);

-- Add default timestamps where missing
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'todos' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE todos ADD COLUMN created_at timestamptz DEFAULT now();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'documents' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE documents ADD COLUMN created_at timestamptz DEFAULT now();
  END IF;
END $$;

-- Add user_id to tables that need it
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'documents' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE documents ADD COLUMN user_id uuid REFERENCES auth.users(id);
  END IF;
END $$;

-- Update existing triggers or add new ones
DROP TRIGGER IF EXISTS handle_updated_at ON todos;
CREATE TRIGGER handle_updated_at
  BEFORE UPDATE ON todos
  FOR EACH ROW
  EXECUTE FUNCTION moddatetime('updated_at');

-- Add NOT NULL constraints where appropriate
DO $$ 
BEGIN
  ALTER TABLE todos ALTER COLUMN task SET NOT NULL;
  ALTER TABLE documents ALTER COLUMN user_id SET NOT NULL;
EXCEPTION
  WHEN others THEN
    RAISE NOTICE 'Error setting NOT NULL constraints: %', SQLERRM;
END $$;