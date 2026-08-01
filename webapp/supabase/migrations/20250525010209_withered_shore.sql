/*
  # Add initial admin user

  1. Changes
    - Creates initial admin user in auth.users
    - Adds admin role entry in user_roles table
    - Sets up necessary permissions
*/

-- Create initial admin user if not exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM auth.users WHERE email = 'admin@codette.ai'
  ) THEN
    INSERT INTO auth.users (
      instance_id,
      id,
      aud,
      role,
      email,
      encrypted_password,
      email_confirmed_at,
      created_at,
      updated_at
    )
    VALUES (
      '00000000-0000-0000-0000-000000000000',
      gen_random_uuid(),
      'authenticated',
      'authenticated',
      'admin@codette.ai',
      crypt('admin123', gen_salt('bf')), -- Change this password in production!
      now(),
      now(),
      now()
    );
  END IF;
END $$;

-- Add admin role for the user
DO $$
DECLARE
  admin_user_id uuid;
BEGIN
  SELECT id INTO admin_user_id FROM auth.users WHERE email = 'admin@codette.ai';
  
  IF NOT EXISTS (
    SELECT 1 FROM user_roles WHERE user_id = admin_user_id AND role = 'admin'
  ) THEN
    INSERT INTO user_roles (user_id, role)
    VALUES (admin_user_id, 'admin');
  END IF;
END $$;