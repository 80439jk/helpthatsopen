import './globals.css';
import type { Metadata } from 'next';
import { SITE } from '@/lib/db';

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: 'CornerHelp', template: '%s · CornerHelp' },
  description:
    'We don’t take applications. We tell you who’s open. Local assistance programs, ' +
    'confirmed by phone.',
};

/** The disclosure bar and footer disclaimer are required on every page and must not be
 *  removed, collapsed, or conditionally rendered (.cursorrules rule 2). They live in
 *  the layout so no route can omit them. */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap"
        />
      </head>
      <body>
        <div className="disclosure">
          <div className="wrap">
            CornerHelp is an independent private company. Not a government agency, and not
            affiliated with any government program.
          </div>
        </div>
        <header className="site">
          <div className="wrap">
            <a className="brand" href="/">
              <span className="pane" aria-hidden="true" />
              <span className="brandname">CornerHelp</span>
            </a>
            <div className="promise">We don&rsquo;t take applications. We tell you who&rsquo;s open.</div>
          </div>
        </header>
        <main>{children}</main>
        <footer className="site">
          <div className="wrap">
            CornerHelp is an independent private company. We are not a government agency, we are
            not affiliated with any government program, and we do not provide assistance or accept
            applications. Every status on this site was confirmed by telephone with the provider on
            the date shown. <a href="/how-we-verify/">How we verify</a> ·{' '}
            <a href="/corrections/">Corrections</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
