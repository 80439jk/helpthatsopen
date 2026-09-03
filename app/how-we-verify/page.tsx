export const metadata = { title: 'How we verify' };
export default function HowWeVerify() {
  return (
    <div className="wrap stack">
      <h1>How we verify</h1>
      <p>
        Every status on this site came from a telephone call to the provider. We do not scrape
        it, we do not infer it, and we do not carry it over from last month.
      </p>
      <h2>What the statuses mean</h2>
      <ul className="plain">
        <li><b>Accepting applications</b> — they told us they were taking applications on the
          date shown.</li>
        <li><b>Waiting list</b> — they are open but you will be placed in a queue.</li>
        <li><b>Funds out for now</b> — the money for this cycle is gone. This is shown in grey,
          not red, because it is information rather than an emergency.</li>
        <li><b>Not confirmed</b> — we have not reached them recently enough to say. We show this
          rather than guess.</li>
      </ul>
      <h2>How often we re-check</h2>
      <p>
        Crisis funds that refill monthly are re-checked every 14 days. Waiting lists every 45
        days, stable services every 90, and statewide hotlines every 180. When a listing passes
        its re-check date it stops appearing as confirmed until someone has called again.
      </p>
      <h2>When an agency will not confirm</h2>
      <p>
        We try three times, on different days and at different times. After that the listing
        shows as not confirmed and says so plainly. An honest &ldquo;we could not reach
        them&rdquo; is more useful than a stale green.
      </p>
      <h2>What we are not</h2>
      <p>
        CornerHelp is an independent private company. We are not a government agency, we are not
        affiliated with any government program, and we do not accept, file or process
        applications. We are a directory.
      </p>
    </div>
  );
}
