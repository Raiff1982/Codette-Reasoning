/*
  # Add get_user_role function
  
  1. New Functions
    - `get_user_role`: Returns the role of the authenticated user
  
  2. Security
    - Function is only accessible to authenticated users
    - Returns the user's role from user_roles table
*/

-- Create function to get user role
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TABLE (role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT ur.role
  FROM public.user_roles ur
  WHERE ur.user_id = auth.uid()
  LIMIT 1;
END;
$$;