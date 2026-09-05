/** Call centre hours: 9:00 a.m. – 9:00 p.m. Eastern, Monday to Friday.
 *
 *  The prototype said "someone is answering right now" as a flat claim. It can
 *  be a true one instead: check the clock. Outside hours the page says when we
 *  open rather than promising a pickup that will not happen.
 *
 *  Evaluated in the BROWSER, not at build time -- pages are cached for five
 *  minutes and a cached "we're open" would outlive closing time.
 */
export const HOURS_LABEL = 'Monday–Friday, 9:00 a.m.–9:00 p.m. ET';

export function easternNow(now = new Date()) {
  const f = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: 'numeric',
    minute: 'numeric', hour12: false,
  }).formatToParts(now);
  const g = (t: string) => f.find((p) => p.type === t)?.value ?? '';
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return { day: days.indexOf(g('weekday')), hour: Number(g('hour')) % 24,
           minute: Number(g('minute')) };
}

export function isOpenNow(now = new Date()) {
  const { day, hour } = easternNow(now);
  return day >= 1 && day <= 5 && hour >= 9 && hour < 21;
}

/** "Opens at 9:00 a.m. ET" / "Opens Monday at 9:00 a.m. ET" */
export function opensNext(now = new Date()) {
  const { day, hour } = easternNow(now);
  const weekday = day >= 1 && day <= 5;
  if (weekday && hour < 9) return 'Opens at 9:00 a.m. ET';
  if (day === 5 && hour >= 21) return 'Opens Monday at 9:00 a.m. ET';
  if (day === 6 || day === 0) return 'Opens Monday at 9:00 a.m. ET';
  return 'Opens tomorrow at 9:00 a.m. ET';
}
