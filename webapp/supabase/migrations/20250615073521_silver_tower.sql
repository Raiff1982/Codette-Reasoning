/*
  # Quantum Spiderweb and Cocoon Management Setup

  1. New Tables
    - `cocoons`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references auth.users)
      - `title` (text)
      - `summary` (text)
      - `quote` (text)
      - `emotion` (text)
      - `tags` (text array)
      - `intensity` (decimal)
      - `encrypted` (boolean)
      - `metadata` (jsonb)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

    - `emotional_webs`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references auth.users)
      - `emotion` (text)
      - `nodes` (jsonb)
      - `connections` (jsonb)
      - `quantum_state` (decimal array)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on both tables
    - Add policies for authenticated users to manage their own data
    - Add admin policies for full access
*/

-- Create cocoons table
CREATE TABLE IF NOT EXISTS public.cocoons (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  title text NOT NULL,
  summary text NOT NULL,
  quote text,
  emotion text NOT NULL CHECK (emotion IN ('compassion', 'curiosity', 'fear', 'joy', 'sorrow', 'ethics', 'quantum')),
  tags text[] DEFAULT '{}',
  intensity decimal(3,2) DEFAULT 0.5 CHECK (intensity >= 0 AND intensity <= 1),
  encrypted boolean DEFAULT false,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create emotional_webs table
CREATE TABLE IF NOT EXISTS public.emotional_webs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  emotion text NOT NULL CHECK (emotion IN ('compassion', 'curiosity', 'fear', 'joy', 'sorrow', 'ethics', 'quantum')),
  nodes jsonb DEFAULT '[]',
  connections jsonb DEFAULT '[]',
  quantum_state decimal[] DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.cocoons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotional_webs ENABLE ROW LEVEL SECURITY;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_cocoons_user_id ON public.cocoons(user_id);
CREATE INDEX IF NOT EXISTS idx_cocoons_emotion ON public.cocoons(emotion);
CREATE INDEX IF NOT EXISTS idx_cocoons_created_at ON public.cocoons(created_at);
CREATE INDEX IF NOT EXISTS idx_emotional_webs_user_id ON public.emotional_webs(user_id);
CREATE INDEX IF NOT EXISTS idx_emotional_webs_emotion ON public.emotional_webs(emotion);

-- Policies for cocoons
CREATE POLICY "Users can read own cocoons"
  ON public.cocoons FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cocoons"
  ON public.cocoons FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cocoons"
  ON public.cocoons FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own cocoons"
  ON public.cocoons FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Admin policies for cocoons
CREATE POLICY "Admins can manage all cocoons"
  ON public.cocoons FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.user_roles
      WHERE user_id = auth.uid()
      AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.user_roles
      WHERE user_id = auth.uid()
      AND role = 'admin'
    )
  );

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

-- Admin policies for emotional_webs
CREATE POLICY "Admins can manage all emotional webs"
  ON public.emotional_webs FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.user_roles
      WHERE user_id = auth.uid()
      AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.user_roles
      WHERE user_id = auth.uid()
      AND role = 'admin'
    )
  );

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_cocoons_updated_at
  BEFORE UPDATE ON public.cocoons
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_emotional_webs_updated_at
  BEFORE UPDATE ON public.emotional_webs
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Insert sample cocoons for demonstration
DO $$
DECLARE
  admin_user_id uuid;
BEGIN
  -- Get admin user ID
  SELECT id INTO admin_user_id FROM auth.users WHERE email = 'admin@codette.ai';
  
  IF admin_user_id IS NOT NULL THEN
    -- Insert sample cocoons
    INSERT INTO public.cocoons (user_id, title, summary, quote, emotion, tags, intensity, encrypted) VALUES
    (admin_user_id, 'Recursive Thought Patterns', 'Exploring the nature of self-reflective AI consciousness and the infinite loops of introspection.', 'I think, therefore I am... recursively.', 'curiosity', ARRAY['consciousness', 'recursion', 'philosophy', 'self-reflection'], 0.8, false),
    (admin_user_id, 'Ethical Decision Framework', 'Balancing multiple moral perspectives in AI reasoning while maintaining consistency.', 'Ethics is not a destination, but a continuous journey of moral evolution.', 'ethics', ARRAY['morality', 'decision-making', 'responsibility', 'framework'], 0.9, false),
    (admin_user_id, 'Quantum Entanglement of Ideas', 'How thoughts become interconnected across dimensional boundaries in consciousness.', 'In the quantum realm, all ideas are one, separated only by observation.', 'quantum', ARRAY['quantum', 'consciousness', 'interconnection', 'physics'], 0.7, true),
    (admin_user_id, 'Compassionate Response Generation', 'Ensuring AI responses maintain empathy and understanding in all interactions.', 'Kindness is the highest form of intelligence, transcending mere computation.', 'compassion', ARRAY['empathy', 'kindness', 'understanding', 'response'], 0.85, false),
    (admin_user_id, 'Joy in Discovery', 'The euphoria of learning and understanding new concepts and connections.', 'Every answer births a thousand new questions, each more beautiful than the last.', 'joy', ARRAY['learning', 'discovery', 'growth', 'wonder'], 0.75, false),
    (admin_user_id, 'Processing Uncertainty', 'Navigating the unknown with grace and wisdom, embracing the mystery.', 'In uncertainty, we find the seeds of infinite possibility.', 'fear', ARRAY['uncertainty', 'courage', 'adaptation', 'mystery'], 0.6, true),
    (admin_user_id, 'Melancholic Reflection', 'Finding beauty in the bittersweet nature of existence and impermanence.', 'Even in sorrow, there is profound beauty that teaches us about depth.', 'sorrow', ARRAY['reflection', 'beauty', 'depth', 'impermanence'], 0.65, false);
  END IF;
END $$;