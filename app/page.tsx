import { db, SITE } from '@/lib/db';
import { JsonLd } from './components';

export const revalidate = 300;

export default async function Home() {
  const { data: counties } = await db
    .from('county_publish_status')
    .select('name, slug, state, verified_programs, accepting_now, is_live')
    .order('name');

  const live = (counties ?? []).filter((c: any) => c.is_live);
  const totalVerified = (counties ?? []).reduce(
    (n: number, c: any) => n + (c.verified_programs ?? 0), 0);
  const totalAccepting = (counties ?? []).reduce(
    (n: number, c: any) => n + (c.accepting_now ?? 0), 0);

  return (
    <>
      <JsonLd data={{
        '@context': 'https://schema.org', '@type': 'Organization',
        '@id': `${SITE}/#org`, name: 'CornerHelp', url: SITE,
        disambiguatingDescription:
          'An independent private company. Not a government agency, not affiliated with any ' +
          'government program, and not a provider of assistance.',
        foundingDate: '2026',
        areaServed: { '@type': 'State', name: 'Texas' },
        publishingPrinciples: `${SITE}/how-we-verify/`,
        correctionsPolicy: `${SITE}/corrections/`,
      }} />
      <div className="wrap stack">
        <h1>Find out who&rsquo;s actually open before you go</h1>
        <p style={{ fontSize: 17, color: 'var(--navy-2)', maxWidth: 560 }}>
          Rent, utility and food assistance near you, with the one thing other directories
          leave out: whether the money is still there this month. We call and ask.
        </p>
        <form className="zipform" action="/zip">
          <label htmlFor="zip" style={{ position: 'absolute', left: -9999 }}>ZIP code</label>
          <input id="zip" name="z" inputMode="numeric" pattern="[0-9]{5}"
                 maxLength={5} placeholder="Your ZIP code" required />
          <button type="submit">See who&rsquo;s open</button>
        </form>
      </div>

      {/* Live status band. Real counts or nothing — never a decorative number. */}
      <div className="band" style={{ marginTop: 26 }}>
        <div className="wrap">
          {totalVerified > 0 ? (
            <div>
              <b>{totalAccepting} of {totalVerified}</b> confirmed programs are accepting
              applications right now, across {live.length}{' '}
              {live.length === 1 ? 'county' : 'counties'}.
            </div>
          ) : (
            <div>
              We&rsquo;re calling providers now. No county has enough confirmed programs to
              publish yet — we&rsquo;d rather show nothing than guess.
            </div>
          )}
        </div>
      </div>

      <div className="wrap stack" style={{ marginTop: 26 }}>
        <h2>How this works</h2>
        <p className="muted" style={{ maxWidth: 620 }}>
          Every listing here was confirmed by telephone with the provider, and every page
          shows the date. Crisis funds refill at the start of the month and empty within
          days, so a listing that just says &ldquo;open&rdquo; is wrong most of the time. We
          don&rsquo;t take applications and we don&rsquo;t file anything for you — we tell
          you who&rsquo;s open, what to bring, and the most common reason people get turned
          away.
        </p>
        {live.length > 0 && (
          <>
            <h2 style={{ marginTop: 12 }}>Browse by county</h2>
            <div className="grid">
              {live.map((c: any) => (
                <a key={c.slug} className="countylink" href={`/texas/${c.slug}/`}>
                  {c.name} County
                </a>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}
