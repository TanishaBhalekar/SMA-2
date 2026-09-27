import { createClient } from '@supabase/supabase-js';

const rawUrl = (import.meta.env.VITE_SUPABASE_URL || '').trim();
const cleanUrl = rawUrl.replace(/\/(rest|auth)\/v\d+[\/]?$/, '').replace(/\/+$/, '');
const cleanAnonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim();

export const supabase = createClient(cleanUrl, cleanAnonKey);
