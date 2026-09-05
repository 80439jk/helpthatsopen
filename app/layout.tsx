import './globals.css';
import type { Metadata } from 'next';
import { SITE } from '@/lib/db';
import { HOME } from '@/lib/routes';
import { CALL_CENTER_PHONE, prettyPhone } from '@/lib/site';
import { PrototypeSwitcher } from './switcher';

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: 'CornerHelp', template: '%s · CornerHelp' },
  description:
    'Which rent, utility and food assistance programs are accepting applications ' +
    'right now. Confirmed by phone, dated on every listing.',
  robots: { index: false, follow: false },
};

export function Mark({ size = 26, id = 'wm' }: { size?: number; id?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <defs><clipPath id={id}>
        <rect x="2.6" y="2.6" width="20.8" height="20.8" rx="4.4" />
      </clipPath></defs>
      <g clipPath={`url(#${id})`}><rect x="13" y="0" width="14" height="13" fill="#C41F4E" /></g>
      <rect x="2" y="2" width="22" height="22" rx="5" fill="none" stroke="#C41F4E" strokeWidth="3" />
      <path d="M13 3.5v19M3.5 13h19" stroke="#C41F4E" strokeWidth="2.4" />
    </svg>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const tel = CALL_CENTER_PHONE;
  return (
    <html lang="en">
      <body>
        <div className="disc-bar">
          Independent private company. Not a government website. Not a government program.
        </div>

        <div className="wrap"><div className="nav">
          <a className="logo" href={HOME}><Mark size={27} id="wm1" />CornerHelp</a>
          <ul>
            <li><a href="/how-we-verify/">How we check</a></li>
            <li><a href="/corrections/">Corrections</a></li>
          </ul>
          <div className="navr">
            {/* renders only when a real number exists — lib/site.ts */}
            {tel && <a className="navtel" href={`tel:${tel}`}>{prettyPhone(tel)}</a>}
            <a className="btn" href={HOME}>Check my ZIP</a>
          </div>
        </div></div>

        {children}

        <footer><div className="wrap">
          <div className="fg">
            <div>
              <div className="fbrand"><Mark id="wm2" />CornerHelp</div>
              <p>
                Independent private company. We publish program status — we don&rsquo;t
                provide assistance and we don&rsquo;t handle applications.
              </p>
              {tel && <p className="fphone">{prettyPhone(tel)}</p>}
            </div>
            <div>
              <h4>What we track</h4>
              <a href={HOME}>Rent &amp; eviction</a><a href={HOME}>Electric &amp; gas</a>
              <a href={HOME}>Water</a><a href={HOME}>Food</a>
            </div>
            <div>
              <h4>About</h4>
              <a href="/how-we-verify/">How we verify</a>
              <a href="/corrections/">Corrections log</a>
            </div>
          </div>
        </div>
        <div className="footbar"><div className="wrap">
          <p>
            CornerHelp is an independent private company publishing the current application
            status of assistance programs operated by other organizations. We are not
            affiliated with, endorsed by, or connected to any government agency or program.
            We do not provide financial assistance, prepare applications, submit
            applications, or represent applicants to any agency. Statuses are confirmed by
            direct contact with each provider and are accurate as of the date shown on each
            listing; funding and waitlists change without notice, so confirm with the
            provider before travelling. The directory is free.
          </p>
        </div></div>
        </footer>

        <PrototypeSwitcher />
      </body>
    </html>
  );
}
