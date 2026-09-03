import { db } from '@/lib/db';
export const metadata = { title: 'Corrections' };
export const revalidate = 300;

export default async function Corrections() {
  const { data } = await db.from('corrections')
    .select('reported_at, field, was, now_is, resolved_at, programs(name)')
    .eq('is_public', true).order('reported_at', { ascending: false }).limit(100);
  const rows = data ?? [];
  return (
    <div className="wrap stack">
      <h1>Corrections</h1>
      <p>
        Every correction we make to a listing is recorded here, dated, whether it came from the
        agency, a visitor, or our own team. If something on this site is wrong, tell us and it
        will appear on this page.
      </p>
      {rows.length === 0 ? (
        <p className="muted">No corrections recorded yet.</p>
      ) : (
        <ul className="plain">
          {rows.map((c: any, i: number) => (
            <li key={i} className="card">
              <div className="org">
                {new Date(c.reported_at).toLocaleDateString('en-US',
                  { year: 'numeric', month: 'long', day: 'numeric' })}
              </div>
              <div><b>{c.programs?.name}</b> — {c.field}</div>
              <div className="facts"><div>was: {c.was}</div><div>now: {c.now_is}</div></div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
