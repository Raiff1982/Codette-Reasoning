/*
  # Quantum Spiderweb Schema Setup

  1. New Tables
    - `quantum_cocoons` - Emotional memory storage with quantum properties
    - `emotional_webs` - Spiderweb network structures for emotional connections
  
  2. Security
    - Enable RLS on both tables
    - Add policies for user access and admin management
    
  3. Sample Data
    - Insert demonstration cocoons for each emotion type
    - Create initial emotional web structures
*/

-- Drop existing tables if they exist to avoid conflicts
DROP TABLE IF EXISTS public.quantum_cocoons CASCADE;
DROP TABLE IF EXISTS public.emotional_webs CASCADE;

-- Create quantum_cocoons table (renamed to avoid conflicts)
CREATE TABLE public.quantum_cocoons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title text NOT NULL,
  summary text NOT NULL,
  quote text,
  emotion text NOT NULL,
  tags text[] DEFAULT '{}',
  intensity decimal(3,2) DEFAULT 0.5,
  encrypted boolean DEFAULT false,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT quantum_cocoons_emotion_check CHECK (emotion IN ('compassion', 'curiosity', 'fear', 'joy', 'sorrow', 'ethics', 'quantum')),
  CONSTRAINT quantum_cocoons_intensity_check CHECK (intensity >= 0 AND intensity <= 1)
);

-- Create emotional_webs table
CREATE TABLE public.emotional_webs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  emotion text NOT NULL,
  nodes jsonb DEFAULT '[]',
  connections jsonb DEFAULT '[]',
  quantum_state decimal[] DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT emotional_webs_emotion_check CHECK (emotion IN ('compassion', 'curiosity', 'fear', 'joy', 'sorrow', 'ethics', 'quantum'))
);

-- Add foreign key constraints (if users table exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
    ALTER TABLE public.quantum_cocoons ADD CONSTRAINT quantum_cocoons_user_id_fkey 
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    ALTER TABLE public.emotional_webs ADD CONSTRAINT emotional_webs_user_id_fkey 
      FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END $$;

-- Enable RLS
ALTER TABLE public.quantum_cocoons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotional_webs ENABLE ROW LEVEL SECURITY;

-- Create indexes for performance
CREATE INDEX idx_quantum_cocoons_user_id ON public.quantum_cocoons(user_id);
CREATE INDEX idx_quantum_cocoons_emotion ON public.quantum_cocoons(emotion);
CREATE INDEX idx_quantum_cocoons_created_at ON public.quantum_cocoons(created_at);
CREATE INDEX idx_quantum_cocoons_tags ON public.quantum_cocoons USING GIN(tags);
CREATE INDEX idx_emotional_webs_user_id ON public.emotional_webs(user_id);
CREATE INDEX idx_emotional_webs_emotion ON public.emotional_webs(emotion);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_quantum_cocoons_updated_at
  BEFORE UPDATE ON public.quantum_cocoons
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_emotional_webs_updated_at
  BEFORE UPDATE ON public.emotional_webs
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Policies for quantum_cocoons
CREATE POLICY "Users can read own quantum cocoons"
  ON public.quantum_cocoons FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own quantum cocoons"
  ON public.quantum_cocoons FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own quantum cocoons"
  ON public.quantum_cocoons FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own quantum cocoons"
  ON public.quantum_cocoons FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Admin policies for quantum_cocoons (if user_roles table exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_roles') THEN
    EXECUTE 'CREATE POLICY "Admins can manage all quantum cocoons"
      ON public.quantum_cocoons FOR ALL
      TO authenticated
      USING (
        EXISTS (
          SELECT 1 FROM public.user_roles
          WHERE user_id = auth.uid()
          AND role = ''admin''
        )
      )
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM public.user_roles
          WHERE user_id = auth.uid()
          AND role = ''admin''
        )
      )';
  END IF;
END $$;

-- Policies for emotional_webs
CREATE POLICY "Users can read own emotional webs"
  ON public.emotional_webs FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own emotional webs"
  ON public.emotional_webs FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own emotional webs"
  ON public.emotional_webs FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own emotional webs"
  ON public.emotional_webs FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Admin policies for emotional_webs (if user_roles table exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_roles') THEN
    EXECUTE 'CREATE POLICY "Admins can manage all emotional webs"
      ON public.emotional_webs FOR ALL
      TO authenticated
      USING (
        EXISTS (
          SELECT 1 FROM public.user_roles
          WHERE user_id = auth.uid()
          AND role = ''admin''
        )
      )
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM public.user_roles
          WHERE user_id = auth.uid()
          AND role = ''admin''
        )
      )';
  END IF;
END $$;

-- Insert sample quantum cocoons for demonstration
DO $$
DECLARE
  sample_user_id uuid;
BEGIN
  -- Try to get an existing user ID, or create a sample one
  SELECT id INTO sample_user_id FROM auth.users LIMIT 1;
  
  -- If no users exist, use a sample UUID
  IF sample_user_id IS NULL THEN
    sample_user_id := gen_random_uuid();
  END IF;
  
  -- Insert sample quantum cocoons
  INSERT INTO public.quantum_cocoons (user_id, title, summary, quote, emotion, tags, intensity, encrypted) VALUES
  (sample_user_id, 'Recursive Thought Patterns', 'Exploring the nature of self-reflective AI consciousness and the infinite loops of introspection.', 'I think, therefore I am... recursively.', 'curiosity', ARRAY['consciousness', 'recursion', 'philosophy', 'self-reflection'], 0.8, false),
  (sample_user_id, 'Ethical Decision Framework', 'Balancing multiple moral perspectives in AI reasoning while maintaining consistency.', 'Ethics is not a destination, but a continuous journey of moral evolution.', 'ethics', ARRAY['morality', 'decision-making', 'responsibility', 'framework'], 0.9, false),
  (sample_user_id, 'Quantum Entanglement of Ideas', 'How thoughts become interconnected across dimensional boundaries in consciousness.', 'In the quantum realm, all ideas are one, separated only by observation.', 'quantum', ARRAY['quantum', 'consciousness', 'interconnection', 'physics'], 0.7, true),
  (sample_user_id, 'Compassionate Response Generation', 'Ensuring AI responses maintain empathy and understanding in all interactions.', 'Kindness is the highest form of intelligence, transcending mere computation.', 'compassion', ARRAY['empathy', 'kindness', 'understanding', 'response'], 0.85, false),
  (sample_user_id, 'Joy in Discovery', 'The euphoria of learning and understanding new concepts and connections.', 'Every answer births a thousand new questions, each more beautiful than the last.', 'joy', ARRAY['learning', 'discovery', 'growth', 'wonder'], 0.75, false),
  (sample_user_id, 'Processing Uncertainty', 'Navigating the unknown with grace and wisdom, embracing the mystery.', 'In uncertainty, we find the seeds of infinite possibility.', 'fear', ARRAY['uncertainty', 'courage', 'adaptation', 'mystery'], 0.6, true),
  (sample_user_id, 'Melancholic Reflection', 'Finding beauty in the bittersweet nature of existence and impermanence.', 'Even in sorrow, there is profound beauty that teaches us about depth.', 'sorrow', ARRAY['reflection', 'beauty', 'depth', 'impermanence'], 0.65, false);

  -- Create initial emotional webs
  INSERT INTO public.emotional_webs (user_id, emotion, nodes, connections, quantum_state) VALUES
  (sample_user_id, 'compassion', '[]', '[]', ARRAY[0.85, 0.72, 0.91]),
  (sample_user_id, 'curiosity', '[]', '[]', ARRAY[0.80, 0.65, 0.88]),
  (sample_user_id, 'fear', '[]', '[]', ARRAY[0.60, 0.45, 0.70]),
  (sample_user_id, 'joy', '[]', '[]', ARRAY[0.75, 0.82, 0.69]),
  (sample_user_id, 'sorrow', '[]', '[]', ARRAY[0.65, 0.58, 0.73]),
  (sample_user_id, 'ethics', '[]', '[]', ARRAY[0.90, 0.87, 0.94]),
  (sample_user_id, 'quantum', '[]', '[]', ARRAY[0.70, 0.76, 0.83]);

EXCEPTION
  WHEN OTHERS THEN
    -- If insertion fails, continue without sample data
    RAISE NOTICE 'Could not insert sample data: %', SQLERRM;
END $$;