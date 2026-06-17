import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Data Contract CLI',
  tagline: 'Lint, test, and export data contracts from the command line',
  favicon: 'img/favicon.ico',

  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
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
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Data Contract CLI',
      logo: {
        alt: 'Data Contract CLI',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          href: 'https://editor.datacontract.com',
          label: 'Editor',
          position: 'right',
        },
        {
          href: 'https://pypi.org/project/datacontract-cli/',
          label: 'PyPI',
          position: 'right',
        },
        {
          href: 'https://github.com/datacontract/datacontract-cli',
          label: 'GitHub',
          position: 'right',
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
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Data Contract CLI authors. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'sql', 'yaml', 'python', 'json', 'docker'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
