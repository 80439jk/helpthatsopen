import { createClient } from '@supabase/supabase-js';

// Read-only anon client. Every table this queries is public directory data.
export const db = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  { auth: { persistSession: false } }
);

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
