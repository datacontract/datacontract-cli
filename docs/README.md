# Website

This website is built using [Docusaurus](https://docusaurus.io/), a modern static website generator.

## Installation

```bash
yarn
```

## Local Development

```bash
yarn start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server.

## Build

```bash
yarn build
```

This command generates static content into the `build` directory and can be served using any static contents hosting service.

## URLs and redirects

`static/staticwebapp.config.json` is the deployed redirect layer. Docusaurus
emits a static site with no server, so this file is the only place a 301 can
live. It ships because Docusaurus copies `static/` verbatim into `build/`.

(The Deployment section below is stock Docusaurus boilerplate and describes
`gh-pages`; the site actually deploys to Azure Static Web Apps from
`.github/workflows/azure-static-web-apps-docs.yml`.)

This works with `trailingSlash: false` in `docusaurus.config.ts`, and the two
settings have to agree. Docusaurus decides what each page's canonical URL *is*;
this file makes the host enforce it.

Left unset, Docusaurus wrote `build/commands/index.html` while canonicalising to
`/commands` — and Azure served every intermediate form too, so each page
answered `200` at four URLs with only the canonical tag to sort them out:

```
/commands   /commands/   /commands/index.html   /commands/index
```

Worse, the site disagreed with itself: category index pages canonicalised
*with* a slash (`/commands/dbt/`, `/commands/export/`, `/commands/import/`,
`/scheduling/`) while the other 195 pages did not. No host-level rule can be
right for both halves, which is why the Docusaurus setting had to change first
rather than this one carrying the whole fix.

Now every page emits a flat `commands/dbt.html`, canonicalises to
`/commands/dbt`, and `"trailingSlash": "auto"` redirects the leftovers onto it.
`auto` and `never` behave identically for a flat layout like this; `auto` is
preferred because it is verified in production to leave `/` at `200`, and it is
what the other Entropy Data sites use.

The two `/index` routes exist because `auto` mishandles the root, and only the
root: with no folder segment to fall back to, Azure strips `.html` like an
ordinary file and lands on `/index`, which answers `200` straight back from
`index.html`. The routes send both forms to `/`.

Note that route rules drop the query string — Azure's `redirect` is a static
string with no placeholder syntax. The `trailingSlash` redirects preserve it, so
only the two explicit rules are affected.

## Deployment

Using SSH:

```bash
USE_SSH=true yarn deploy
```

Not using SSH:

```bash
GIT_USER=<Your GitHub username> yarn deploy
```

If you are using GitHub pages for hosting, this command is a convenient way to build the website and push to the `gh-pages` branch.
