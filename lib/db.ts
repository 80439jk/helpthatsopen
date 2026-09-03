import { createClient, SupabaseClient } from '@supabase/supabase-js';

/** Lazily constructed.
 *
 *  Creating the client at module scope ran it during `next build` page-data collection —
 *  including for /_not-found, which never queries anything — so a missing env var failed
 *  the whole build with "supabaseUrl is required" rather than one page at request time.
 *  Building and running are different moments and only one of them needs credentials. */
let _db: SupabaseClient | null = null;

export function getDb(): SupabaseClient {
  if (_db) return _db;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error(
      'Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and ' +
      'NEXT_PUBLIC_SUPABASE_ANON_KEY (see .env.example).'
    );
  }
  _db = createClient(url, key, { auth: { persistSession: false } });
  return _db;
}

/** True when the app can reach a database at all. Pages use this to degrade to an honest
 *  message instead of a 500 — a directory that says "we can't load this right now" is
 *  still better than a stack trace. */
export const dbConfigured = () =>
  Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

export const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://cornerhelp.com';

/** .cursorrules rule 7: never fabricate freshness. This is the only place a status
 *  becomes a label, and unknown is a real answer rather than a blank. */
export const STATUS_LABEL: Record<string, string> = {
  accepting: 'Accepting applications',
  waitlist: 'Waiting list',
  funds_exhausted: 'Funds out for now',
  seasonal_closed: 'Closed for the season',
  appointment_only: 'By appointment only',
  unknown: 'Not confirmed',
};

/** Crimson is brand and action only, never a status (.cursorrules design tokens).
 *  Funds-out is grey, not red: the reader is already panicking and red reads as alarm. */
export const STATUS_TONE: Record<string, 'open' | 'wait' | 'shut'> = {
  accepting: 'open',
  waitlist: 'wait',
  appointment_only: 'wait',
  funds_exhausted: 'shut',
  seasonal_closed: 'shut',
  unknown: 'shut',
};

export function whenVerified(iso: string | null): string {
  if (!iso) return 'not yet confirmed';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'confirmed today';
  if (days === 1) return 'confirmed yesterday';
  if (days < 14) return `confirmed ${days} days ago`;
  return `confirmed ${new Date(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}`;
}
