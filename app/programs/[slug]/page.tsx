import { notFound } from 'next/navigation';
import { getDb, dbConfigured, SITE, STATUS_LABEL, whenVerified } from '@/lib/db';
import { StatusPill, JsonLd } from '../../components';
import type { Metadata } from 'next';

export const revalidate = 300;

async function load(slug: string) {
  if (!dbConfigured()) return null;
  const { data } = await getDb().from('programs')
    .select('slug, name, current_status, last_verified_at, intake_phone, how_to_apply, ' +
            'documents_required, disqualifier, application_window, stated_service_area, ' +
            'service_area_verified, organizations(name, website, org_type)')
    .eq('slug', slug).maybeSingle();
  return data as any;
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const p = await load(params.slug);
  if (!p) return { title: 'Not found' };
  const confirmed = p.current_status && p.current_status !== 'unknown';
  return {
    title: `${p.name} — ${p.organizations?.name ?? ''}`.trim(),
    description: confirmed
      ? `${STATUS_LABEL[p.current_status]}. ${whenVerified(p.last_verified_at)}.`
      : `We have not yet confirmed the current status of this program by phone.`,
    alternates: { canonical: `${SITE}/programs/${p.slug}/` },
    robots: confirmed ? undefined : { index: false, follow: true },
  };
}

export default async function Program({ params }: { params: { slug: string } }) {
  const p = await load(params.slug);
  if (!p) notFound();
  const confirmed = p.current_status && p.current_status !== 'unknown';

  return (
    <>
      {confirmed && (
        <JsonLd data={{
          '@context': 'https://schema.org', '@type': 'Service',
          '@id': `${SITE}/programs/${p.slug}/#service`,
          name: p.name,
          // NGO provider, never GovernmentService — structured data is a machine-readable
          // claim and marking these as government would contradict the whole positioning.
          provider: {
            '@type': p.organizations?.org_type === 'municipal_utility' ? 'Organization' : 'NGO',
            name: p.organizations?.name, url: p.organizations?.website ?? undefined,
          },
          ...(p.documents_required?.length
            ? { termsOfService: p.documents_required.join(', ') } : {}),
          ...(p.intake_phone ? {
            availableChannel: {
              '@type': 'ServiceChannel',
              servicePhone: { '@type': 'ContactPoint', telephone: p.intake_phone },
            },
          } : {}),
        }} />
      )}
      <div className="wrap stack">
        <div className="crumb"><a href="/">CornerHelp</a> › Programs › {p.name}</div>
        {p.organizations?.name && <div className="org">{p.organizations.name}</div>}
        <h1>{p.name}</h1>
        <div><StatusPill status={p.current_status} /></div>
        <div className="verified">{whenVerified(p.last_verified_at)}</div>

        {!confirmed && (
          <div className="notlive">
            <b>We haven&rsquo;t reached this program yet.</b>
            <p className="muted" style={{ margin: '8px 0 0' }}>
              The details below came from the provider&rsquo;s own published information and
              have not been confirmed by phone. Call before you travel.
            </p>
          </div>
        )}

        <div className="facts" style={{ marginTop: 6 }}>
          {p.how_to_apply && <div><b>How to apply:</b> {p.how_to_apply.replace(/_/g, ' ')}</div>}
          {p.application_window && <div><b>Timing:</b> {p.application_window}</div>}
          {p.documents_required?.length ? (
            <div><b>What to bring:</b> {p.documents_required.join(' · ')}</div>) : null}
          {p.stated_service_area && (
            <div>
              <b>Service area:</b> {p.stated_service_area}
              {!p.service_area_verified && (
                <span className="muted"> (not yet confirmed with the provider)</span>
              )}
            </div>
          )}
        </div>

        {p.disqualifier && (
          <div className="catch"><b>The most common reason people get turned away:</b>{' '}
            {p.disqualifier}</div>
        )}

        {p.intake_phone && (
          <div><a className="tel" href={`tel:${p.intake_phone}`}>Call {p.intake_phone}</a></div>
        )}

        <p className="muted" style={{ marginTop: 14 }}>
          This is the provider&rsquo;s own number. CornerHelp does not take applications and is
          not affiliated with this organization. Something wrong?{' '}
          <a href="/corrections/">Tell us</a>.
        </p>
      </div>
    </>
  );
}
