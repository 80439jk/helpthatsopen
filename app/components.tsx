import { STATUS_LABEL, STATUS_TONE, verifiedParts } from '@/lib/db';
import { CALL_CENTER_PHONE } from '@/lib/site';

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

/** What to say on a listing the visitor can't use today.
 *
 *  Only where this door is shut AND another on the same page is open -- offering
 *  to find "what's open now" when nothing is open would be a lie, and it is
 *  exactly the lie a directory in this category would tell. Never on an
 *  accepting listing: there the right action is to ring the agency, whose number
 *  is right there. That is .cursorrules rule 5 in one function. */
function nudge(status: string | null, elsewhereOpen: number, reopens?: string | null) {
  if (!CALL_CENTER_PHONE || elsewhereOpen < 1) return null;
  switch (status) {
    case 'funds_exhausted':
      return `Out of money here. Ask us which ${elsewhereOpen === 1 ? 'one is' : `${elsewhereOpen} are`} open now →`;
    case 'seasonal_closed':
      return reopens ? `Closed until then. Ask us what's open now →`
                     : `Closed for the season. Ask us what's open now →`;
    case 'waitlist':
      return `There's a queue here. Ask us who's taking people faster →`;
    case 'appointment_only':
      return `Appointment only. Ask us who takes walk-ins →`;
    default:
      return null;
  }
}

export function ProgramCard(
  { p, href, elsewhereOpen = 0 }:
  { p: ProgramRow; href?: string; elsewhereOpen?: number }) {
  const tone = STATUS_TONE[p.current_status ?? 'unknown'] ?? 'shut';
  const v = verifiedParts(p.last_verified_at);
  const ask = nudge(p.current_status, elsewhereOpen, p.application_window);
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

        {ask && (
          <a className="stuck" href={`tel:${CALL_CENTER_PHONE}`}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3 2.5h2.6l1.2 3-1.6 1.1a8.5 8.5 0 0 0 3.9 3.9l1.1-1.6 3 1.2V13a1 1 0
                       0 1-1.1 1A11.6 11.6 0 0 1 2 3.6 1 1 0 0 1 3 2.5Z" fill="#fff" />
            </svg>{ask}
          </a>
        )}

        <p className="Lver">
          <b>{v.relative}</b>
          {v.absolute && (
            <time dateTime={p.last_verified_at ?? undefined}>{v.absolute}</time>
          )}
        </p>
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
        Dialling <b>211</b> also reaches the statewide referral line, free.
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
