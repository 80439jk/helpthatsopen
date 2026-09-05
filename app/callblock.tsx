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

/** Sticky bar, mobile only. The prototype put it on the results view and it is
 *  the highest-value placement on the page -- on a phone the listings run past
 *  the fold and the CTA above them is long gone. It states the real count for
 *  this place, so it is a summary before it is an ad. */
export function StickyCall({ accepting, place }: { accepting: number; place: string }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const tick = () => setOpen(isOpenNow());
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, []);
  if (!CALL_CENTER_PHONE) return null;
  return (
    <div className="sticky">
      <div>
        <b>{accepting} open in {place}</b>
        <small>{open ? 'Find out which ones fit you' : opensNext()}</small>
      </div>
      <a className="btn" href={`tel:${CALL_CENTER_PHONE}`}>Call</a>
    </div>
  );
}

/** End of the list. Someone who has read every card and not picked one is the
 *  person this is for -- which is why it sits after them, not before. */
export function ListEndCall({ count }: { count: number }) {
  if (!CALL_CENTER_PHONE) return null;
  return (
    <div className="rcta">
      <div className="rctaL">
        <h3>Still not sure which one to try first?</h3>
        <p>
          Someone will go through these {count} with you — which will take your situation,
          what order to go in, and whether your paperwork will hold up. We don&rsquo;t apply
          for you. We just make sure you don&rsquo;t waste the trip.
        </p>
      </div>
      <a className="btn" href={`tel:${CALL_CENTER_PHONE}`}>
        Talk it through — {prettyPhone(CALL_CENTER_PHONE)}
      </a>
    </div>
  );
}
