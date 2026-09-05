import { STATUS_LABEL, STATUS_TONE, whenVerified } from '@/lib/db';

export type ProgramRow = {
  slug: string; name: string; org_name: string | null;
  current_status: string | null; last_verified_at: string | null;
  intake_phone: string | null; how_to_apply: string | null;
  documents_required: string[] | null; disqualifier: string | null;
  application_window: string | null; stated_service_area: string | null;
};

export function StatusPill({ status }: { status: string | null }) {
  const s = status ?? 'unknown';
  const tone = STATUS_TONE[s] ?? 'shut';
  return <span className={`Lstate ${tone}`}>{STATUS_LABEL[s] ?? 'Not confirmed'}</span>;
}

export function ProgramCard({ p, href }: { p: ProgramRow; href?: string }) {
  const tone = STATUS_TONE[p.current_status ?? 'unknown'] ?? 'shut';
  return (
    <article className="L">
      <span className={`w ${tone === 'open' ? 'o' : tone === 'wait' ? 't' : 's'}`} />
      <div>
        <div className="Ltop">
          <div className="Lorg">
            {href ? <a href={href} style={{ color: 'inherit' }}>{p.org_name ?? p.name}</a>
                  : (p.org_name ?? p.name)}
          </div>
          <StatusPill status={p.current_status} />
        </div>
        <p className="Lprog">{p.name}</p>

        {/* The field nobody else publishes, in the agency's own words. */}
        {p.disqualifier && (
          <div className="Lnote"><b>Most common reason people are turned away:</b>{' '}
            {p.disqualifier}</div>
        )}

        <dl>
          {p.how_to_apply && (<><dt>Apply</dt><dd>{p.how_to_apply.replace(/_/g, ' ')}</dd></>)}
          {p.application_window && (<><dt>Timing</dt><dd>{p.application_window}</dd></>)}
          {p.documents_required?.length
            ? (<><dt>Bring</dt><dd>{p.documents_required.join(' · ')}</dd></>) : null}
          {p.stated_service_area && (<><dt>Area</dt><dd>{p.stated_service_area}</dd></>)}
          {p.intake_phone && (<><dt>Call</dt>
            <dd><a className="tel" href={`tel:${p.intake_phone}`}>{p.intake_phone}</a></dd></>)}
        </dl>

        <p className="Lver">{whenVerified(p.last_verified_at)}</p>
      </div>
    </article>
  );
}

/** A ZIP or county below the publish threshold. Rule 7 says do not serve stale green;
 *  it does not say serve a void. Saying plainly that we have not confirmed here yet is
 *  the honest answer and is still more useful than a directory that guesses. */
export function NotLiveYet(
  { place, pending, known = 0 }:
  { place: string; pending: number; known?: number }) {
  return (
    <div className="notlive stack">
      <h2>We haven&rsquo;t confirmed enough programs in {place} yet</h2>
      <p className="muted">
        We only list a program once someone here has called and confirmed both that it is
        open and which areas it actually covers. We would rather show you nothing than send
        you to a closed door.
      </p>
      {pending > 0 ? (
        <p className="muted">
          {pending} {pending === 1 ? 'program is' : 'programs are'} part-way through that process
          right now.
        </p>
      ) : known > 0 ? (
        <p className="muted">
          We know of {known} {known === 1 ? 'program' : 'programs'} serving {place}. None has
          been called yet.
        </p>
      ) : null}
      <p className="muted">
        In the meantime, dialling <b>211</b> reaches the statewide referral line.
      </p>
    </div>
  );
}

export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
