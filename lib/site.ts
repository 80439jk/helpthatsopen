/** Site-wide facts that are business decisions, not code.
 *
 * CALL_CENTER_PHONE is empty until a real number exists. Every phone CTA in the
 * design renders only when it is set, so the layout is finished and nothing
 * advertises a number that does not answer. Set it here in E.164 and it appears
 * in the header and on the results page at once.
 *
 * .cursorrules rule 5: a commercial handoff is bounded by timing and consent.
 * This number reaches a licensed call center, never an agency, and the page must
 * say so plainly wherever it appears.
 */
export const CALL_CENTER_PHONE = '+18888881000';

export const prettyPhone = (e164: string) =>
  /^\+1\d{10}$/.test(e164)
    ? `(${e164.slice(2, 5)}) ${e164.slice(5, 8)}-${e164.slice(8)}`
    : e164;

/** The prototypes and landers the floating switcher offers. */
export const PROTOTYPES = [
  { href: '/preview/prototype.html',   name: 'Landing + results',
    what: 'The design of record' },
  { href: '/preview/va-console.html',  name: 'Verification console',
    what: 'What the caller sees' },
  { href: '/preview/logo-system.html', name: 'Logo system',
    what: 'Marks, colour, status palette' },
  { href: '/legacy/',                  name: 'Legacy static landing',
    what: 'The original coming-soon page' },
  { href: '/',                         name: 'All versions',
    what: 'The full index' },
];
