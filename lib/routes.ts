/** Where the live product lives.
 *
 * Pre-launch, "/" is an internal index of every version of this thing that
 * exists, so opening the deployment shows the whole set rather than dropping
 * straight into the app. The app itself sits at /app/.
 *
 * To put the product back at the root, change this to '/' and move
 * app/app/page.tsx back to app/page.tsx. Every link that means "home"
 * reads this, so that is the whole change.
 */
export const HOME = '/app/';

/** Markets, and the URL segment each one uses.
 *
 * The route used to be a literal /texas/ directory, so an Asheville ZIP was
 * served at /texas/28801/ with a breadcrumb reading "Texas". Adding a market
 * is now one line here.
 */
export const STATES: Record<string, { name: string; slug: string }> = {
  TX: { name: 'Texas', slug: 'texas' },
  NC: { name: 'North Carolina', slug: 'north-carolina' },
  FL: { name: 'Florida', slug: 'florida' },
};

export const STATE_BY_SLUG: Record<string, string> = Object.fromEntries(
  Object.entries(STATES).map(([code, s]) => [s.slug, code]),
);

/** "/north-carolina/28801/" — the canonical path for a ZIP or county slug. */
export function placePath(stateCode: string, place: string) {
  const s = STATES[stateCode];
  return s ? `/${s.slug}/${place}/` : `/${place}/`;
}
