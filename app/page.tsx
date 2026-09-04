import { HOME } from '@/lib/routes';

export const metadata = {
  title: 'CornerHelp — versions',
  robots: { index: false, follow: false },
};

type Item = {
  href: string;
  name: string;
  what: string;
  live?: boolean;
};

const ITEMS: Item[] = [
  {
    href: HOME,
    name: 'Live app',
    what: 'The real thing. ZIP search, county pages, program pages, reading current status ' +
          'straight from the database. Nothing publishes until it has been confirmed by phone.',
    live: true,
  },
  {
    href: '/preview/prototype.html',
    name: 'Landing + results',
    what: 'Single-file mockup of the visitor journey — homepage through to a results list ' +
          'with open, waitlist and closed states. Design reference, not wired to data.',
  },
  {
    href: '/preview/va-console.html',
    name: 'Verification console',
    what: 'What the caller sees: the queue, the call script, and the fields captured on ' +
          'each call. Mockup of the tool the call sheet currently stands in for.',
  },
  {
    href: '/preview/logo-system.html',
    name: 'Logo system',
    what: 'Marks, lockups, colour tokens and the open/waitlist/closed status palette.',
  },
  {
    href: '/legacy/',
    name: 'Legacy static landing',
    what: 'The coming-soon page this deployment served before the app existed. Kept for ' +
          'reference; superseded by the live app.',
  },
];

export default function Versions() {
  return (
    <div className="wrap stack">
      <h1>Versions</h1>
      <p className="muted" style={{ maxWidth: 620 }}>
        Everything that currently exists in this repo, in one place. This index is
        internal — the whole deployment sits behind Vercel Authentication and carries a
        noindex header.
      </p>

      <div className="stack" style={{ gap: 0, marginTop: 8 }}>
        {ITEMS.map((it) => (
          <a
            key={it.href}
            href={it.href}
            style={{
              display: 'block',
              padding: '20px 0',
              borderTop: '2px solid var(--line)',
              color: 'inherit',
              textDecoration: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 19, fontWeight: 800 }}>{it.name}</span>
              {it.live && (
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 800,
                    letterSpacing: '.08em',
                    textTransform: 'uppercase',
                    color: 'var(--open)',
                  }}
                >
                  live
                </span>
              )}
              <span className="muted" style={{ fontSize: 13.5, marginLeft: 'auto' }}>
                {it.href}
              </span>
            </div>
            <p className="muted" style={{ margin: '8px 0 0', maxWidth: 620, fontSize: 15 }}>
              {it.what}
            </p>
          </a>
        ))}
      </div>
    </div>
  );
}
