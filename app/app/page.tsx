import { getDb, dbConfigured, SITE } from '@/lib/db';
import { JsonLd } from '../components';
import { placePath, STATES } from '@/lib/routes';

export const revalidate = 300;

/** The landing page, ported from preview/prototype.html.
 *
 *  Every number on it is real. The prototype shows 3,180 of 11,840 because a
 *  mockup needs something in the box; this reads the gate. When the counts are
 *  small they say so -- a fake 8,930 on a site whose entire claim is "somebody
 *  checked" would be the one lie that matters. */
export default async function Home() {
  const counties = dbConfigured()
    ? ((await getDb().from('county_publish_status')
        .select('name, slug, state, verified_programs, accepting_now, total_programs, is_live')
        .order('accepting_now', { ascending: false })).data ?? [])
    : [];
  const zips = dbConfigured()
    ? ((await getDb().from('zip_publish_status')
        .select('verified_programs, accepting_now, is_live')).data ?? [])
    : [];

  const live = counties.filter((c: any) => c.is_live);
  const totalVerified = counties.reduce((n: number, c: any) => n + (c.verified_programs ?? 0), 0);
  const accepting = counties.reduce((n: number, c: any) => n + (c.accepting_now ?? 0), 0);
  const notOpen = Math.max(totalVerified - accepting, 0);
  const pct = totalVerified ? Math.round((accepting / totalVerified) * 100) : 0;
  const liveZips = zips.filter((z: any) => z.is_live).length;
  const states = Array.from(new Set(live.map((c: any) => c.state)))
    .map((s) => STATES[s as string]?.name).filter(Boolean);

  return (
    <>
      <JsonLd data={{
        '@context': 'https://schema.org', '@type': 'Organization',
        '@id': `${SITE}/#org`, name: 'CornerHelp', url: SITE,
        disambiguatingDescription:
          'An independent private company. Not a government agency, not affiliated with any ' +
          'government program, and not a provider of assistance.',
        foundingDate: '2026',
        areaServed: Object.values(STATES).map((s) => ({ '@type': 'State', name: s.name })),
        publishingPrinciples: `${SITE}/how-we-verify/`,
        correctionsPolicy: `${SITE}/corrections/`,
      }} />

      <section className="hero"><div className="wrap herog">
        <div>
          <p className="eyebrow">
            {totalVerified > 0 ? `${totalVerified} programs confirmed by phone` : 'Calling now'}
          </p>
          <h1>Who&rsquo;s accepting applications near you today.</h1>

          {totalVerified > 0 ? (
            <div className="ratio">
              <div className="rnums">
                <div className="rn o"><b>{accepting.toLocaleString()}</b>
                  <small>accepting applications</small></div>
                <div className="rn c"><b>{notOpen.toLocaleString()}</b>
                  <small>waitlisted or out of money</small></div>
              </div>
              <div className="bar"><i style={{ width: `${pct}%` }} /></div>
              <div className="bar-l">
                <span>{pct}% of {totalVerified.toLocaleString()} confirmed programs are open right now</span>
                <span>{liveZips.toLocaleString()} ZIP{liveZips === 1 ? '' : 's'} live</span>
              </div>
            </div>
          ) : (
            <div className="ratio">
              <div className="bar-l" style={{ borderTop: 0, paddingTop: 0 }}>
                <span>No county has enough confirmed programs to publish yet. We&rsquo;d
                      rather show nothing than guess.</span>
              </div>
            </div>
          )}

          <p className="body">
            The expensive part is finding out at the door. We call every program and put the
            date on it, so you know before you go.
          </p>
        </div>

        <div className="zcard">
          <div className="zcard-h">Check your ZIP</div>
          <div className="zcard-b">
            <form action="/zip">
              <label htmlFor="z" className="hide">ZIP code</label>
              <input className="zin" id="z" name="z" maxLength={5} inputMode="numeric"
                     pattern="[0-9]{5}" placeholder="ZIP code" required />
              <button className="btn" type="submit">See who&rsquo;s open →</button>
            </form>
            <ul className="gets">
              <li><span className="tick"><Tick /></span>
                <div><b>Who&rsquo;s open today</b>
                  <small>Confirmed by phone, not scraped off a list</small></div></li>
              <li><span className="tick"><Tick /></span>
                <div><b>What to bring</b>
                  <small>The exact document list for each place</small></div></li>
              <li><span className="tick"><Tick /></span>
                <div><b>Who to try first</b>
                  <small>So you&rsquo;re not making four trips</small></div></li>
            </ul>
          </div>
        </div>
      </div></section>

      <div className="vp"><div className="wrap vpg">
        <div>
          <p className="eyebrow" style={{ color: 'var(--pink)' }}>What we are</p>
          <h2>We don&rsquo;t take applications. We tell you who&rsquo;s open.</h2>
          <p>
            That&rsquo;s the whole service. No forms, no filing, no representing you to
            anybody. We find out who has money this week and what they&rsquo;ll ask you for,
            and then you go do it yourself.
          </p>
          <p style={{ marginBottom: 0 }}>Free, and there&rsquo;s nothing to sign up for.</p>
        </div>
        <ul className="nots">
          <li><span className="x">✕</span>We don&rsquo;t fill out your application</li>
          <li><span className="x">✕</span>We don&rsquo;t submit anything on your behalf</li>
          <li><span className="x">✕</span>We don&rsquo;t represent you to any agency</li>
          <li><span className="x">✕</span>We don&rsquo;t decide who qualifies</li>
          <li><span className="x yes">✓</span>
            <span className="yes">We tell you who&rsquo;s open, what they need, and who to try first</span></li>
        </ul>
      </div></div>

      <section><div className="wrap">
        <p className="eyebrow">The only three words that matter</p>
        <h2 className="s">Every listing says whether the money is still there.</h2>
        <p className="sub">
          Most directories give you a phone number and let you find out the hard way. Ours
          carries a status and the date we confirmed it — the same lit window you see in our name.
        </p>
        <div className="trio">
          <div className="sbox"><h3><i className="w o" />Accepting</h3>
            <p>Taking applications today, funds available as of our last call. Check the hours
               before you go — most of these cap intake.</p></div>
          <div className="sbox"><h3><i className="w t" />Waitlist</h3>
            <p>Still taking your information, but there&rsquo;s a queue. Worth starting anyway —
               the clock runs from the day you apply.</p></div>
          <div className="sbox"><h3><i className="w s" />Funds out</h3>
            <p>Spent for this cycle. Most refill at the start of the month. We show the
               reopening date when the agency gives us one.</p></div>
        </div>
      </div></section>

      <section className="alt" id="verify"><div className="wrap vg">
        <div>
          <p className="eyebrow">How we check</p>
          <h2 className="s">We call. That&rsquo;s the whole trick.</h2>
          <p className="sub">
            There&rsquo;s no feed for this. No agency publishes &ldquo;we ran out of rent money
            on the 6th.&rdquo; So a person picks up the phone, asks, writes down the answer and
            the date, and we show you both.
          </p>
          <p className="sub" style={{ marginBottom: 0 }}>
            If a date looks old to you, it should. We&rsquo;d rather show it than hide it.
          </p>
        </div>
        <div>
          <div className="tier"><div><b>Funds-cycling programs</b>
            <small>Crisis utility, emergency rent, energy assistance</small></div>
            <em>every 14 days</em></div>
          <div className="tier"><div><b>Waitlist programs</b>
            <small>Housing authority lists, vouchers</small></div><em>every 45 days</em></div>
          <div className="tier"><div><b>Stable programs</b>
            <small>Pantries, clinics, weatherization</small></div><em>every 90 days</em></div>
          <div className="tier"><div><b>Fixed services</b>
            <small>Statewide lines, referral centers</small></div><em>every 180 days</em></div>
        </div>
      </div></section>

      {live.length > 0 && (
        <section><div className="wrap">
          <p className="eyebrow">
            {states.length ? states.join(' · ') : 'Live now'}
          </p>
          <h2 className="s">Start with your county.</h2>
          <p className="sub">
            What&rsquo;s open, what each place requires, and when we last confirmed it.
          </p>
          <div className="cgrid">
            {live.map((c: any) => (
              <a key={`${c.state}-${c.slug}`} className="cty" href={placePath(c.state, c.slug)}>
                <span>{c.name}</span>
                <em>{c.accepting_now}/{c.verified_programs}</em>
              </a>
            ))}
          </div>
        </div></section>
      )}

      <section className="alt"><div className="wrap split">
        <div className="panel">
          <h3>Run one of these programs?</h3>
          <p>
            Tell us what we have wrong — funding, waitlist, hours, documents — and we&rsquo;ll
            fix it the same day. It means fewer people at your door on a day you can&rsquo;t
            help them.
          </p>
          <p>
            Every correction goes in a public log with the date on it.{' '}
            <a href="/corrections/">Corrections</a>.
          </p>
        </div>
        <div className="panel">
          <h3>Who keeps this current</h3>
          <p>
            A person calls each program on a schedule set by how fast its money moves, and
            records what they were told and when. Nothing is published from a website scrape
            or a model.
          </p>
          <p><a href="/how-we-verify/">How we verify</a>.</p>
        </div>
      </div></section>
    </>
  );
}

function Tick() {
  return (
    <svg width="15" height="15" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2.6 7.4l2.9 2.9 5.9-6.6" stroke="#C41F4E" strokeWidth="2.4"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
