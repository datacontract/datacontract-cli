// Umami click tracking for cli.datacontract.com (registered as a Docusaurus client module).
//
// 1. Tags important links with data-umami-event (Umami's tracker handles the click and records the page path):
//    links to Entropy Data, the Data Contract Editor, GitHub (incl. the star button), Slack, PyPI and ODCS.
// 2. Tracks copies from code blocks ("copy-code" with the first line, e.g. `pip install datacontract-cli`).
// 3. Adds UTM parameters to links that go to Entropy Data. Docusaurus renders external links with
//    rel="noopener noreferrer", which drops the referrer, so without UTM these visits arrive as "direct"
//    on entropy-data.com and the CLI -> Entropy Data path is invisible in the lead funnel.
// Hand-placed data-umami-event attributes always win.

const RULES = [
  ['auto-to-entropy-data-sign-up', /\/\/app\.entropy-data\.com\/(create-account|signup|register)/],
  ['auto-to-entropy-data-demo', /\/\/demo\.entropy-data\.com/],
  ['auto-to-entropy-data-api', /\/\/api\.entropy-data\.com/],
  ['auto-to-entropy-data', /\/\/(www\.|app\.|docs\.)?entropy-data\.com/],
  ['auto-to-datacontract-editor', /\/\/editor\.datacontract\.com/],
  ['auto-github-star', /\/\/github\.com\/datacontract\/datacontract-cli\/?([?#]|$)/],
  ['auto-to-github', /\/\/github\.com\/(datacontract|bitol-io|entropy-data)\b/],
  ['auto-join-slack', /datacontract\.com\/slack|\.slack\.com\//],
  ['auto-to-pypi', /\/\/pypi\.org\/project\/datacontract-cli/],
  ['auto-to-odcs', /\/\/bitol-io\.github\.io\/open-data-contract-standard/],
  ['auto-to-datacontract-com', /\/\/(www\.)?datacontract\.com/],
];
// legal pages are neither an action nor marketing traffic: not tagged, no UTM
const SKIP = /entropy-data\.com\/(legal-notice|privacy-policy)/;
const NO_UTM = /api\.entropy-data\.com/;

function area(a) {
  return a.closest('.navbar, nav') ? 'nav' : a.closest('footer') ? 'footer' : 'content';
}

function tagLink(a) {
  if (a.hasAttribute('data-umami-event')) return;
  const href = a.href || '';
  if (SKIP.test(href)) return;
  const rule = RULES.find((r) => r[1].test(href));
  if (!rule) return;
  a.setAttribute('data-umami-event', rule[0]);
  a.setAttribute('data-umami-event-area', area(a));
  const label = (a.getAttribute('aria-label') || a.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
  if (label) a.setAttribute('data-umami-event-label', label);
  if (/entropy-data\.com/.test(href) && !NO_UTM.test(href)) {
    const url = new URL(href);
    if (!url.searchParams.has('utm_source')) {
      url.searchParams.set('utm_source', 'cli.datacontract.com');
      url.searchParams.set('utm_medium', 'referral');
      url.searchParams.set('utm_content', window.location.pathname.slice(0, 80));
      a.setAttribute('href', url.toString());
    }
  }
}

function tagAll() {
  document.querySelectorAll('a[href]').forEach(tagLink);
}

if (typeof window !== 'undefined') {
  // Docusaurus' code-block copy button: track which snippets get copied.
  document.addEventListener('click', (e) => {
    const btn = e.target.closest && e.target.closest('button[aria-label^="Copy code"], button[class*="copyButton"]');
    if (!btn || !window.umami) return;
    const code = btn.closest('.theme-code-block, [class*="codeBlockContainer"], [class*="codeBlockContent"]')?.querySelector('pre code, pre');
    const text = (code?.innerText || '').trim();
    window.umami.track('copy-code', { snippet: text.split('\n')[0].slice(0, 80), lines: text ? text.split('\n').length : 0 });
  }, true);
}

// Called by Docusaurus after the initial render and after every client-side navigation.
export function onRouteDidUpdate() {
  // the new page's DOM is in place at this point; navbar/footer links are tagged once and stay tagged
  window.setTimeout(tagAll, 0);
}
