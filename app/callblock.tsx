'use client';
import { useEffect, useState } from 'react';
import { CALL_CENTER_PHONE, prettyPhone } from '@/lib/site';
import { HOURS_LABEL, isOpenNow, opensNext } from '@/lib/hours';

/** The call CTA. Renders closed-state on the server so the first paint is never
 *  a promise we can't keep, then corrects to the live state on mount. */
export function CallBlock({ accepting, verified }: { accepting: number; verified: number }) {
  const [open, setOpen] = useState(false);
  const [when, setWhen] = useState(HOURS_LABEL);
  useEffect(() => {
    const tick = () => { setOpen(isOpenNow()); setWhen(opensNext()); };
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, []);

  if (!CALL_CENTER_PHONE) return null;
  return (
    <div className="zero">
      <div className="zeroL">
        <p className="zlab">
          {open ? <><span className="zdot" />Someone is answering right now</>
                : <>{when}</>}
        </p>
        <h3>Not sure which of these to try first?</h3>
        <p className="zerostat">
          <b>{accepting}</b> of these {verified} are open today.
        </p>
        <p className="zsub">
          Talk it through with someone who has the same list in front of them — which ones
          fit your situation, what to bring, and the order to try them.
        </p>
      </div>
      <div className="zeroR">
        <a className="zeronum" href={`tel:${CALL_CENTER_PHONE}`}>
          {prettyPhone(CALL_CENTER_PHONE)}
        </a>
        <a className="btn" href={`tel:${CALL_CENTER_PHONE}`}>
          {open ? 'Call now' : 'Call when we open'}
        </a>
        <p className="zeromicro">
          {HOURS_LABEL} · free · we don&rsquo;t take applications · not a government line
        </p>
      </div>
    </div>
  );
}
