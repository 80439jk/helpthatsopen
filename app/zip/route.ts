import { NextRequest, NextResponse } from 'next/server';
import { getDb, dbConfigured } from '@/lib/db';
import { placePath } from '@/lib/routes';

/** Path is canonical (.cursorrules). The form posts a query param; we redirect to
 *  the path form so no indexable duplicate is ever created.
 *
 *  The state has to be looked up, not assumed. This redirected every ZIP to
 *  /texas/ regardless, which put Asheville in Texas. */
export async function GET(req: NextRequest) {
  const z = (req.nextUrl.searchParams.get('z') ?? '').replace(/\D/g, '').slice(0, 5);
  if (z.length !== 5) return NextResponse.redirect(new URL('/', req.url));

  let code = '';
  if (dbConfigured()) {
    const { data } = await getDb().from('zip_counties')
      .select('counties(state)').eq('zip', z).limit(1).maybeSingle();
    code = (data as any)?.counties?.state ?? '';
  }
  // An unknown ZIP goes home rather than to a made-up state path.
  if (!code) return NextResponse.redirect(new URL('/', req.url));
  return NextResponse.redirect(new URL(placePath(code, z), req.url));
}
