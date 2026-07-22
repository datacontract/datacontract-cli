import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Several syntax-highlighting colours in the stock Prism themes fall below the
 * WCAG AA 4.5:1 threshold against their own code-block background (e.g. the
 * light theme's `#36acaa` at 2.58:1, and Dracula's comment grey at 3.03:1).
 * Remap just those tokens to a darker/lighter shade of the same hue so code
 * blocks stay readable without changing the overall look.
 */
function withAccessibleTokenColors(
  theme: typeof prismThemes.github,
  replacements: Record<string, string>,
) {
  return {
    ...theme,
    styles: theme.styles.map((entry) => {
      const color = entry.style?.color;
      const replacement = color && replacements[color];
      return replacement
        ? {...entry, style: {...entry.style, color: replacement}}
        : entry;
    }),
  };
}

const lightCodeTheme = withAccessibleTokenColors(prismThemes.github, {
  '#999988': '#717161', // comment
  '#e3116c': '#da1067', // string, attr-value
  '#36acaa': '#277b7a', // number, boolean, property, variable, …
  '#00a4db': '#0078a0', // keyword, attr-name, selector
  '#d73a49': '#d42d3d', // function, tag, deleted
});

const darkCodeTheme = withAccessibleTokenColors(prismThemes.dracula, {
  'rgb(98, 114, 164)': 'rgb(134, 146, 185)', // comment
});

const config: Config = {
  title: 'Data Contract CLI',
  tagline: 'Lint, test, and export data contracts from the command line',
  favicon: 'img/favicon.png',

  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
    // Rspack/SWC/LightningCSS toolchain (@docusaurus/faster): faster builds and
    // smaller, more aggressively minified CSS/JS bundles.
    faster: true,
  },

  // Production url of the documentation site.
  url: 'https://docs.datacontract.com',
  baseUrl: '/',

  organizationName: 'datacontract',
  projectName: 'datacontract-cli',

  onBrokenLinks: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          // Serve the docs at the site root (docs-only mode).
          routeBasePath: '/',
          editUrl:
            'https://github.com/datacontract/datacontract-cli/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
        sitemap: {
          // Raise the priority of the main hub pages so crawlers can
          // distinguish them from the long tail of import/export reference pages.
          createSitemapItems: async (params) => {
            const {defaultCreateSitemapItems, ...rest} = params;
            const items = await defaultCreateSitemapItems(rest);
            const hubs: Record<string, number> = {
              'https://docs.datacontract.com/': 1.0,
              'https://docs.datacontract.com/quickstart': 0.9,
              'https://docs.datacontract.com/commands': 0.9,
            };
            return items.map((item) => {
              const priority = hubs[item.url];
              return priority ? {...item, priority} : item;
            });
          },
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      'docusaurus-plugin-llms',
      {
        // Generate /llms.txt (index) and /llms-full.txt (full content) so
        // AI answer engines can ingest the docs as clean markdown.
        generateLLMsTxt: true,
        generateLLMsFullTxt: true,
        // Emit a raw-markdown file for each page so the .md links in llms.txt
        // resolve to served files instead of 404ing.
        generateMarkdownFiles: true,
        docsDir: 'docs',
        title: 'Data Contract CLI',
        description:
          'An open-source command-line tool for working with data contracts based on the Open Data Contract Standard (ODCS).',
        // Emit the docs in a logical learning order so llms.txt reads as a
        // coherent guide instead of an arbitrary file listing.
        includeOrder: [
          'intro.md',
          'quickstart.md',
          'open-data-contract-standard.md',
          'installation.md',
          'editor.md',
          'testing.md',
          'connect/index.md',
          'connect/*.md',
          'quality-rules/index.md',
          'quality-rules/*.md',
          'imports/index.md',
          'imports/*.md',
          'exports/index.md',
          'exports/*.md',
          'commands/index.md',
          'commands/*.md',
          'python-library.md',
          'best-practices.md',
          'dbt.md',
          'api.md',
          'extending.md',
        ],
        includeUnmatchedLast: true,
      },
    ],
  ],

  themes: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        indexBlog: false,
        docsRouteBasePath: '/',
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  themeConfig: {
    image: 'img/datacontractcli.png',
    metadata: [
      {name: 'og:type', content: 'website'},
      {name: 'og:site_name', content: 'Data Contract CLI'},
      {
        name: 'keywords',
        content:
          'data contract, data contract cli, ODCS, Open Data Contract Standard, data quality, data testing, data governance, schema validation, dbt, Snowflake, BigQuery, Databricks',
      },
    ],
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Data Contract CLI',
      logo: {
        // Decorative: the adjacent navbar title already says "Data Contract CLI",
        // so an alt text here would be redundant for screen readers.
        alt: '',
        src: 'img/favicon.png',
        width: 32,
        height: 32,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          href: 'https://github.com/datacontract/datacontract-cli',
          label: 'GitHub',
          position: 'right',
          className: 'navbar-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'What is Data Contract CLI?', to: '/'},
            {label: 'Quickstart', to: '/quickstart'},
            {label: 'Commands', to: '/commands/'},
          ],
        },
        {
          title: 'Community',
          items: [
            {label: 'Slack', href: 'https://datacontract.com/slack'},
            {
              label: 'GitHub',
              href: 'https://github.com/datacontract/datacontract-cli',
            },
            {
              label: 'Open Data Contract Standard',
              href: 'https://bitol-io.github.io/open-data-contract-standard/latest/',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'datacontract.com', href: 'https://datacontract.com'},
            {label: 'Data Contract Editor', href: 'https://editor.datacontract.com'},
            {label: 'PyPI', href: 'https://pypi.org/project/datacontract-cli/'},
          ],
        },
        {
          title: 'Legal',
          items: [
            {label: 'Legal Notice', href: 'https://entropy-data.com/legal-notice'},
            {label: 'Privacy Policy', href: 'https://entropy-data.com/privacy-policy'},
          ],
        },
      ],
      logo: {
        alt: 'Entropy Data',
        // Self-hosted: a third-party request on every page costs a DNS lookup
        // plus a TLS handshake and leaks visitor IPs to another origin.
        src: 'img/entropy-data-logo.svg',
        href: 'https://entropy-data.com',
        width: 148,
        height: 36,
      },
      copyright: `Copyright © ${new Date().getFullYear()} Data Contract CLI authors. Built with Docusaurus.`,
    },
    prism: {
      theme: lightCodeTheme,
      darkTheme: darkCodeTheme,
      additionalLanguages: ['bash', 'sql', 'yaml', 'python', 'json', 'docker'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
