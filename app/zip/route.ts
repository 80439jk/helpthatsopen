import { NextRequest, NextResponse } from 'next/server';

/** Path is canonical (.cursorrules). The form posts a query param; we redirect to the
 *  path form so no indexable duplicate is ever created. */
export function GET(req: NextRequest) {
  const z = (req.nextUrl.searchParams.get('z') ?? '').replace(/\D/g, '').slice(0, 5);
  if (z.length !== 5) return NextResponse.redirect(new URL('/', req.url));
  return NextResponse.redirect(new URL(`/texas/${z}/`, req.url));
}
