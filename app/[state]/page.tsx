import { notFound, redirect } from 'next/navigation';
import type { Metadata } from 'next';
import { getDb, dbConfigured, SITE } from '@/lib/db';
import { JsonLd } from '../components';
import { HOME, STATES, STATE_BY_SLUG, placePath } from '@/lib/routes';
import { CallBlock } from '../callblock';

export const revalidate = 300;

/** State landing page. Two jobs.
 *
 *  For a visitor: what we track here, how much of it we have confirmed, and
 *  which counties are live. Real counts, never a decorative figure.
 *
 *  For paid search: this is where a click lands when Google resolved the
 *  location no finer than the state, and it is where the geo resolver runs. */

const PROGRAM_NAMES: Record<string, { label: string; body: string }> = {
  TX: { label: 'CEAP · CSBG · WAP',
        body: 'Texas runs utility help through CEAP, general and rent assistance through ' +
              'CSBG, and weatherization through WAP — all delivered by local community ' +
              'action agencies under contract to TDHCA, not by the state directly.' },
  NC: { label: 'LIEAP · CIP · Work First',
        body: 'North Carolina delivers energy assistance through county Departments of ' +
              'Social Services. LIEAP heating applications run 1 December to 31 March, ' +
              'with December reserved for applicants aged 60+ and those receiving ' +
              'disability services. Crisis assistance (CIP) runs year round.' },
  FL: { label: 'LIHEAP · EHEAP',
        body: 'Florida assigns one LIHEAP provider per county — a mix of community action ' +
              'agencies, councils on aging and county human services departments. Senior ' +
              'energy assistance moved to FloridaCommerce in July 2026.' },
};

async function resolveGeoTarget(id: string) {
  if (!dbConfigured() || !/^\d{4,12}$/.test(id)) return null;
  const { data } = await getDb().from('google_geo_targets')
    .select('kind, state, zip, counties(slug, state)')
    .eq('criteria_id', Number(id)).maybeSingle();
  if (!data) return null;
  const d = data as any;
  if (d.kind === 'zip' && d.zip) return placePath(d.state, d.zip);
  if (d.kind === 'county' && d.counties) return placePath(d.counties.state, d.counties.slug);
  return null;                       // a state target is already where we are
}

async function load(stateSlug: string) {
  const code = STATE_BY_SLUG[stateSlug];
  if (!code || !dbConfigured()) return null;
  const { data: counties } = await getDb().from('county_publish_status')
    .select('name, slug, state, verified_programs, accepting_now, total_programs, is_live')
    .eq('state', code).order('name');
  return { code, counties: counties ?? [] };
}

export async function generateMetadata(
  { params }: { params: { state: string } }): Promise<Metadata> {
  const code = STATE_BY_SLUG[params.state];
  if (!code) return { title: 'Not found' };
  const name = STATES[code].name;
  return {
    title: `${name} assistance programs — who's accepting applications`,
    description: `Which rent, utility and food assistance programs in ${name} are taking ` +
      `applications right now. Confirmed by phone, with the date on every listing.`,
    alternates: { canonical: `${SITE}/${params.state}/` },
  };
}

export default async function StatePage(
  { params, searchParams }: {
    params: { state: string };
    searchParams: { g?: string; gp?: string };
  }) {
  // Google told us where the click came from. Honour it before rendering the
  // state page — a criteria ID is device-and-intent, not an IP guess.
  const target = searchParams.g ?? searchParams.gp;
  if (target) {
    const to = await resolveGeoTarget(target);
    if (to) redirect(to);
  }

  const d = await load(params.state);
  if (!d) notFound();
  const name = STATES[d.code].name;
  const live = d.counties.filter((c: any) => c.is_live);
  const tracked = d.counties.reduce((n: number, c: any) => n + (c.total_programs ?? 0), 0);
  const confirmed = d.counties.reduce((n: number, c: any) => n + (c.verified_programs ?? 0), 0);
  const accepting = d.counties.reduce((n: number, c: any) => n + (c.accepting_now ?? 0), 0);
  const prog = PROGRAM_NAMES[d.code];

  return (
    <>
      <JsonLd data={{
        '@context': 'https://schema.org', '@type': 'Dataset',
        '@id': `${SITE}/${params.state}/#dataset`,
        name: `${name} assistance program status`,
        creator: { '@id': `${SITE}/#org` },
        spatialCoverage: { '@type': 'State', name },
        measurementTechnique: 'Direct telephone verification with each provider',
        isAccessibleForFree: true,
      }} />

      <div className="crumb"><div className="wrap">
        <a href={HOME}>Home</a> › {name}
      </div></div>

      <div className="rhead"><div className="wrap">
        <p className="eyebrow">{prog?.label}</p>
        <h1>Who&rsquo;s accepting applications in {name} today.</h1>
        {confirmed > 0 ? (
          <p className="rsum">
            <b>{accepting} accepting</b> · {Math.max(confirmed - accepting, 0)} waitlisted
            or out of money · {live.length} count{live.length === 1 ? 'y' : 'ies'} live
          </p>
        ) : (
          <p className="rsum" style={{ color: 'var(--navy-2)' }}>
            {tracked} programs tracked · none confirmed by phone yet
          </p>
        )}
        <form action="/zip" className="rbar">
          <label htmlFor="z" className="hide">ZIP code</label>
          <input className="rzin" id="z" name="z" maxLength={5} inputMode="numeric"
                 pattern="[0-9]{5}" placeholder="Your ZIP code" required />
          <button className="btn" type="submit">See who&rsquo;s open →</button>
        </form>
      </div></div>

      <div className="wrap">
        {live.length > 0 && (
          <CallBlock accepting={accepting} verified={confirmed} />
        )}

        <section style={{ paddingTop: 34 }}>
          <p className="eyebrow">How assistance works here</p>
          <h2 className="s">What {name} runs, and who actually hands it out.</h2>
          <p className="sub">{prog?.body}</p>
        </section>

        <section>
          <p className="eyebrow">
            {live.length > 0
              ? `${live.length} of ${d.counties.length} counties live`
              : `${d.counties.length} counties tracked`}
          </p>
          <h2 className="s">Start with your county.</h2>
          <p className="sub">
            A county goes live once three of its programs have been confirmed by phone.
            {live.length === 0 && ' None here have been called yet — we publish nothing until they have.'}
          </p>
          <div className="cgrid">
            {d.counties.map((c: any) => (
              c.is_live ? (
                <a key={c.slug} className="cty" href={placePath(c.state, c.slug)}>
                  <span>{c.name.replace(' County', '')}</span>
                  <em>{c.accepting_now}/{c.verified_programs}</em>
                </a>
              ) : (
                <span key={c.slug} className="cty off">
                  <span>{c.name.replace(' County', '')}</span>
                  <em style={{ color: 'var(--navy-3)' }}>{c.total_programs}</em>
                </span>
              )
            ))}
          </div>
          <p className="ctynote">
            Grey counties have programs on file that nobody has phoned yet. The number is
            how many we know of.
          </p>
        </section>
      </div>
    </>
  );
}
