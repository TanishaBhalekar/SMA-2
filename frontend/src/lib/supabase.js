import { createClient } from '@supabase/supabase-js';

const rawUrl = (import.meta.env.VITE_SUPABASE_URL || '').trim();
const cleanAnonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim();

console.log("SUPABASE URL:", rawUrl);
console.log("SUPABASE KEY EXISTS:", !!cleanAnonKey);

export const supabase = createClient(rawUrl, cleanAnonKey);
