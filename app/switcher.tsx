'use client';
import { useState } from 'react';
import { PROTOTYPES } from '@/lib/site';

/** Floating switcher. Pre-launch only: it is how you get from the real site to
 *  the prototypes without editing the URL. Remove this component's one line in
 *  layout.tsx to drop it. */
export function PrototypeSwitcher() {
  const [open, setOpen] = useState(false);
  return (
    <div className="psw">
      {open && (
        <div className="psw-menu" role="menu">
          <p>Switch view</p>
          {PROTOTYPES.map((p) => (
            <a key={p.href} href={p.href} role="menuitem">
              {p.name}<small>{p.what}</small>
            </a>
          ))}
        </div>
      )}
      <button className="psw-btn" aria-expanded={open} aria-haspopup="menu"
              aria-label="Switch between the live site and the prototypes"
              onClick={() => setOpen((v) => !v)}>
        {open ? '×' : '▦'}
      </button>
    </div>
  );
}
