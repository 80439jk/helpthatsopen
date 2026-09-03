import { notFound } from 'next/navigation';
import { db, SITE, whenVerified } from '@/lib/db';
import { ProgramCard, NotLiveYet, JsonLd, ProgramRow } from '../../components';
import type { Metadata } from 'next';

export const revalidate = 300;

const PROGRAM_COLS =
  'slug, name, current_status, last_verified_at, intake_phone, how_to_apply, ' +
  'documents_required, disqualifier, application_window, stated_service_area, ' +
  'organizations(name)';

const isZip = (p: string) => /^\d{5}$/.test(p);

async function loadZip(zip: string) {
  const { data: gate } = await db.from('zip_publish_status')
    .select('*').eq('zip', zip).maybeSingle();
  if (!gate) return null;
  const { data: rows } = await db.from('program_zips')
    .select(`programs(${PROGRAM_COLS})`).eq('zip', zip);
  const { data: counties } = await db.from('zip_counties')
    .select('counties(name, slug)').eq('zip', zip);
  return { gate, rows: rows ?? [], counties: counties ?? [], label: `ZIP ${zip}` };
}

async function loadCounty(slug: string) {
  const { data: gate } = await db.from('county_publish_status')
    .select('*').eq('slug', slug).maybeSingle();
  if (!gate) return null;
  const { data: rows } = await db.from('program_counties')
    .select(`programs(${PROGRAM_COLS})`).eq('county_fips', gate.county_fips);
  return { gate, rows: rows ?? [], counties: [], label: `${gate.name} County, Texas` };
}

async function load(place: string) {
  return isZip(place) ? loadZip(place) : loadCounty(place);
}

function flatten(rows: any[]): ProgramRow[] {
  return rows
    .map((r) => r.programs)
    .filter(Boolean)
    .map((p: any) => ({ ...p, org_name: p.organizations?.name ?? null }))
    // fresh first, then anything else; unknown never outranks a confirmed status
    .sort((a: any, b: any) =>
      (b.current_status && b.current_status !== 'unknown' ? 1 : 0) -
      (a.current_status && a.current_status !== 'unknown' ? 1 : 0));
}

export async function generateMetadata(
  { params }: { params: { place: string } }): Promise<Metadata> {
  const d = await load(params.place);
  if (!d) return { title: 'Not found' };
  return {
    title: `Assistance in ${d.label}`,
    description: `Rent, utility and food assistance serving ${d.label}, with current ` +
      `application status confirmed by phone.`,
    alternates: { canonical: `${SITE}/texas/${params.place}/` },
    robots: d.gate.is_live ? undefined : { index: false, follow: true },
  };
}

export default async function Place({ params }: { params: { place: string } }) {
  const d = await load(params.place);
  if (!d) notFound();
  const programs = flatten(d.rows);
  const live = d.gate.is_live;

  return (
    <>
      {live && (
        <JsonLd data={{
          '@context': 'https://schema.org', '@type': 'Dataset',
          '@id': `${SITE}/texas/${params.place}/#dataset`,
          name: `${d.label} assistance program status`,
          description:
            `Current application status, required documents and eligibility for rent, ` +
            `utility, water and food assistance programs serving ${d.label}.`,
          creator: { '@id': `${SITE}/#org` },
          // must equal the real last_verified_at — .cursorrules rule 7
          dateModified: d.gate.last_verified_at,
          spatialCoverage: { '@type': 'AdministrativeArea', name: d.label },
          measurementTechnique: 'Direct telephone verification with each provider',
          isAccessibleForFree: true,
        }} />
      )}
      <div className="wrap stack">
        <div className="crumb"><a href="/">CornerHelp</a> › Texas › {d.label}</div>
        <h1>Assistance in {d.label}</h1>

        {live ? (
          <>
            <p style={{ color: 'var(--navy-2)' }}>
              <b>{d.gate.accepting_now} of {d.gate.verified_programs}</b> confirmed programs
              are accepting applications. Last confirmed {whenVerified(d.gate.last_verified_at)}.
            </p>
            <ul className="plain" style={{ marginTop: 8 }}>
              {programs.map((p) => (
                <ProgramCard key={p.slug} p={p} href={`/programs/${p.slug}/`} />
              ))}
            </ul>
          </>
        ) : (
          <NotLiveYet place={d.label} pending={d.gate.pending_service_area ?? 0} />
        )}

        {isZip(params.place) && d.counties.length > 0 && (
          <p className="muted" style={{ marginTop: 8 }}>
            This ZIP sits in{' '}
            {d.counties.map((c: any, i: number) => (
              <span key={c.counties.slug}>
                {i > 0 && ' and '}
                <a href={`/texas/${c.counties.slug}/`}>{c.counties.name} County</a>
              </span>
            ))}.
          </p>
        )}
      </div>
    </>
  );
}
