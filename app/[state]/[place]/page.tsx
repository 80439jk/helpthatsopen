import { notFound, redirect } from 'next/navigation';
import { getDb, dbConfigured, SITE, whenVerified } from '@/lib/db';
import { ProgramCard, NotLiveYet, JsonLd, ProgramRow } from '../../components';
import { HOME, STATES, STATE_BY_SLUG, placePath } from '@/lib/routes';

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
      <div className="wrap stack">
        <div className="crumb">
          <a href={HOME}>CornerHelp</a> › {d.stateName || 'Not found'} › {d.label}
        </div>
        <h1>Assistance in {d.label}</h1>

        {live ? (
          <>
            <p style={{ color: 'var(--navy-2)' }}>
              <b>{d.gate.accepting_now} of {d.gate.verified_programs}</b> confirmed programs
              are accepting applications. {sentence(whenVerified(d.gate.last_verified_at))}.
            </p>
            <ul className="plain" style={{ marginTop: 8 }}>
              {programs.map((p) => (
                <ProgramCard key={p.slug} p={p} href={`/programs/${p.slug}/`} />
              ))}
            </ul>
          </>
        ) : (
          <NotLiveYet
            place={d.label}
            pending={d.gate.pending_service_area ?? 0}
            known={programs.length}
          />
        )}

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
