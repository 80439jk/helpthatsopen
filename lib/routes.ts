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
