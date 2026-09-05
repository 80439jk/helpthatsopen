import { notFound, redirect } from 'next/navigation';
import { getDb, dbConfigured, SITE, whenVerified } from '@/lib/db';
import { ProgramCard, NotLiveYet, JsonLd, ProgramRow } from '../../components';
import { HOME, STATES, STATE_BY_SLUG, placePath } from '@/lib/routes';
import { CallBlock, StickyCall, ListEndCall, NotLiveCall } from '../../callblock';

const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
import type { Metadata } from 'next';

export const revalidate = 300;

const PROGRAM_COLS =
  'slug, name, current_status, last_verified_at, intake_phone, how_to_apply, ' +
  'documents_required, disqualifier, application_window, stated_service_area, ' +
  'organizations(name)';

const isZip = (p: string) => /^\d{5}$/.test(p);

type Loaded = {
  gate: any; rows: any[]; counties: any[]; label: string;
  stateCode: string; stateName: string; canonical: string;
};

async function loadZip(zip: string): Promise<Loaded | null> {
  const { data: gate } = await getDb().from('zip_publish_status')
    .select('*').eq('zip', zip).maybeSingle();
  if (!gate) return null;
  const [{ data: rows }, { data: counties }] = await Promise.all([
    getDb().from('program_zips').select(`programs(${PROGRAM_COLS})`).eq('zip', zip),
    getDb().from('zip_counties').select('counties(name, slug, state)').eq('zip', zip),
  ]);
  // A ZIP's state comes from the counties it sits in, not from the URL.
  const code = (counties ?? []).map((c: any) => c.counties?.state).find(Boolean) ?? '';
  return {
    gate, rows: rows ?? [], counties: counties ?? [],
    label: `ZIP ${zip}`, stateCode: code,
    stateName: STATES[code]?.name ?? '',
    canonical: placePath(code, zip),
  };
}

async function loadCounty(slug: string, code: string): Promise<Loaded | null> {
  // 26 county slugs repeat across these three states — clay-county is in all
  // of them — so the state is part of the lookup, not decoration.
  const { data: gate } = await getDb().from('county_publish_status')
    .select('*').eq('slug', slug).eq('state', code).maybeSingle();
  if (!gate) return null;
  const { data: rows } = await getDb().from('program_counties')
    .select(`programs(${PROGRAM_COLS})`).eq('county_fips', gate.county_fips);
  return {
    gate, rows: rows ?? [], counties: [],
    label: `${gate.name}, ${STATES[code]?.name ?? code}`,   // gate.name already ends "County"
    stateCode: code, stateName: STATES[code]?.name ?? code,
    canonical: placePath(code, slug),
  };
}

async function load(stateSlug: string, place: string) {
  if (!dbConfigured()) return null;
  const code = STATE_BY_SLUG[stateSlug];
  if (!code) return null;
  return isZip(place) ? loadZip(place) : loadCounty(place, code);
}

function flatten(rows: any[]): ProgramRow[] {
  return rows
    .map((r) => r.programs)
    .filter(Boolean)
    .map((p: any) => ({ ...p, org_name: p.organizations?.name ?? null }))
    .sort((a: any, b: any) =>
      (b.current_status && b.current_status !== 'unknown' ? 1 : 0) -
      (a.current_status && a.current_status !== 'unknown' ? 1 : 0));
}

export async function generateMetadata(
  { params }: { params: { state: string; place: string } }): Promise<Metadata> {
  const d = await load(params.state, params.place);
  if (!d) return { title: 'Not found' };
  return {
    title: `Assistance in ${d.label}`,
    description: `Rent, utility and food assistance serving ${d.label}, with current ` +
      `application status confirmed by phone.`,
    alternates: { canonical: `${SITE}${d.canonical}` },
    robots: d.gate.is_live ? undefined : { index: false, follow: true },
  };
}

export default async function Place({ params }: { params: { state: string; place: string } }) {
  const d = await load(params.state, params.place);
  if (!d) notFound();

  // A ZIP reached under the wrong state redirects to its real one rather than
  // rendering an Asheville ZIP under a Texas breadcrumb.
  if (d.stateCode && d.canonical !== `/${params.state}/${params.place}/`) {
    redirect(d.canonical);
  }

  const programs = flatten(d.rows);
  const live = d.gate.is_live;

  return (
    <>
      {live && (
        <JsonLd data={{
          '@context': 'https://schema.org', '@type': 'Dataset',
          '@id': `${SITE}${d.canonical}#dataset`,
          name: `${d.label} assistance program status`,
          description:
            `Current application status, required documents and eligibility for rent, ` +
            `utility, water and food assistance programs serving ${d.label}.`,
          creator: { '@id': `${SITE}/#org` },
          dateModified: d.gate.last_verified_at,
          spatialCoverage: { '@type': 'AdministrativeArea', name: d.label },
          measurementTechnique: 'Direct telephone verification with each provider',
          isAccessibleForFree: true,
        }} />
      )}
      <div className="crumb"><div className="wrap">
        <a href={HOME}>Home</a> ›{' '}
        <a href={`/${params.state}/`}>{d.stateName || 'Not found'}</a> › {d.label}
      </div></div>

      <div className="rhead"><div className="wrap">
        <p className="eyebrow">
          {live ? `${whenVerified(d.gate.last_verified_at)} · by phone`
                : 'Not confirmed here yet'}
        </p>
        <h1>Assistance in {d.label}</h1>
      </div></div>

      <div className="wrap has-sticky">

        {live ? (
          <>
            <p className="rsum">
              <b>{d.gate.accepting_now} accepting</b> · {Math.max(
                (d.gate.verified_programs ?? 0) - (d.gate.accepting_now ?? 0), 0)}{' '}
              waitlisted or out of money
            </p>

            {/* The commercial handoff. .cursorrules rule 5: it is offered AFTER the
                list, never instead of it, and never framed as the thing that stops a
                disconnection. The agency numbers are above it and always will be. */}
            <CallBlock accepting={d.gate.accepting_now ?? 0}
                       verified={d.gate.verified_programs ?? 0} />

            <div>
              {programs.map((p) => (
                <ProgramCard key={p.slug} p={p} href={`/programs/${p.slug}/`}
                             elsewhereOpen={
                               programs.filter((o) => o.slug !== p.slug &&
                                 o.current_status === 'accepting').length} />
              ))}
            </div>

            <ListEndCall count={programs.length} />

            <div className="what">
              <h3>What happens when you call</h3>
              <ul className="wsteps">
                <li><b>What they do</b>Go through this same list with you and narrow it to
                  the ones that take your situation.</li>
                <li><b>What they ask</b>Your ZIP, what you&rsquo;re behind on, and who lives
                  in the house.</li>
                <li><b>What they don&rsquo;t do</b>Fill out the application, submit it, or
                  represent you to any agency. You do that part yourself.</li>
              </ul>
              <p className="wfoot">
                <span>CornerHelp is not a government agency and is not affiliated with any
                of the programs listed here.</span>
              </p>
            </div>
          </>
        ) : (
          <>
            <NotLiveYet
              place={d.label}
              pending={d.gate.pending_service_area ?? 0}
              known={programs.length}
            />
            <NotLiveCall known={programs.length} place={d.label} />
          </>
        )}

        <StickyCall accepting={d.gate.accepting_now ?? 0} live={live}
                    known={programs.length}
                    place={isZip(params.place) ? params.place : d.gate.name} />

        {isZip(params.place) && d.counties.length > 0 && (
          <p className="muted" style={{ marginTop: 8 }}>
            This ZIP sits in{' '}
            {d.counties.map((c: any, i: number) => (
              <span key={c.counties.slug}>
                {i > 0 && ' and '}
                <a href={placePath(c.counties.state, c.counties.slug)}>{c.counties.name}</a>
              </span>
            ))}.
          </p>
        )}
      </div>
    </>
  );
}
