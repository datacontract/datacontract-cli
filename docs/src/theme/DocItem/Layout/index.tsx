import React, {type ReactNode} from 'react';
import Head from '@docusaurus/Head';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme-original/DocItem/Layout';
import type LayoutType from '@theme/DocItem/Layout';
import type {WrapperProps} from '@docusaurus/types';

type Props = WrapperProps<typeof LayoutType>;

const AUTHORS_ID = 'https://datacontract.com/#authors';
const SOFTWARE_ID = 'https://docs.datacontract.com/#software';

const authors = {
  '@type': 'Organization',
  '@id': AUTHORS_ID,
  name: 'Data Contract CLI authors',
  url: 'https://datacontract.com',
};

/**
 * Answers shown in the "Frequently asked questions" section of `intro.md`.
 * Kept here rather than as JSX in the markdown so that the page stays plain
 * markdown — the llms.txt/llms-full.txt output that AI answer engines ingest
 * is generated from the raw source, and JSX there would leak in as noise.
 * Keep the wording in sync with that section.
 */
const faq: [question: string, answer: string][] = [
  [
    'What is the Data Contract CLI?',
    'The Data Contract CLI (datacontract) is a free and open-source command-line tool, written in Python and published under the MIT license, for linting data contracts, testing real data against them, and importing or exporting them to other schema formats.',
  ],
  [
    'Which data contract format does the Data Contract CLI use?',
    'It natively uses the Open Data Contract Standard (ODCS), an open specification governed by Bitol under the Linux Foundation AI & Data. The legacy Data Contract Specification (DCS) is still supported for reading and as an export target.',
  ],
  [
    'How do I install the Data Contract CLI?',
    'Run "pip install datacontract-cli[all]", or use "uv tool install datacontract-cli[all]". A Docker image is published as datacontract/cli.',
  ],
  [
    'Which data sources can the Data Contract CLI test?',
    'Snowflake, Databricks, Google BigQuery, Amazon Athena, Amazon Redshift, Amazon S3, Azure Blob Storage and ADLS, Google Cloud Storage, Postgres, MySQL, Microsoft SQL Server, Oracle, Trino, Apache Impala, Kafka, Spark DataFrames, JSON HTTP APIs, and local Parquet, JSON, CSV, or Delta files.',
  ],
  [
    'Is the Data Contract CLI free to use?',
    'Yes. It is open source under the MIT license and free for commercial use. Entropy Data offers a commercial platform that the CLI can publish test results to, but the CLI itself does not require it.',
  ],
];

// Homepage: describe the tool itself, the site, and the on-page FAQ, so search
// and answer engines have machine-readable facts to attribute and cite.
const homepageGraph = [
  {
    '@type': 'SoftwareApplication',
    '@id': SOFTWARE_ID,
    name: 'Data Contract CLI',
    alternateName: 'datacontract-cli',
    description:
      'An open-source command-line tool for working with data contracts based on the Open Data Contract Standard (ODCS).',
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'Windows, macOS, Linux',
    programmingLanguage: 'Python',
    url: 'https://docs.datacontract.com/',
    downloadUrl: 'https://pypi.org/project/datacontract-cli/',
    installUrl: 'https://pypi.org/project/datacontract-cli/',
    codeRepository: 'https://github.com/datacontract/datacontract-cli',
    license: 'https://opensource.org/licenses/MIT',
    isAccessibleForFree: true,
    author: {'@id': AUTHORS_ID},
    offers: {'@type': 'Offer', price: '0', priceCurrency: 'USD'},
  },
  authors,
  {
    '@type': 'WebSite',
    '@id': 'https://docs.datacontract.com/#website',
    name: 'Data Contract CLI Documentation',
    url: 'https://docs.datacontract.com/',
    inLanguage: 'en',
    publisher: {'@id': AUTHORS_ID},
    about: {'@id': SOFTWARE_ID},
  },
  {
    '@type': 'FAQPage',
    '@id': 'https://docs.datacontract.com/#faq',
    mainEntity: faq.map(([question, answer]) => ({
      '@type': 'Question',
      name: question,
      acceptedAnswer: {'@type': 'Answer', text: answer},
    })),
  },
];

/**
 * URL of the clean-markdown twin that docusaurus-plugin-llms emits for a page,
 * so agents that prefer markdown can find it from the HTML.
 * `@site/docs/connect/index.md` is written as `/docs/connect/connect.md`.
 */
function markdownUrl(source: string): string {
  const path = source.replace(/^@site\//, '');
  return '/' + path.replace(/([^/]+)\/index\.md$/, '$1/$1.md');
}

/**
 * Wraps the default doc layout to emit JSON-LD structured data on every doc
 * page: TechArticle for reference pages, and a richer graph on the homepage.
 */
export default function LayoutWrapper(props: Props): ReactNode {
  const {metadata} = useDoc();
  const {siteConfig} = useDocusaurusContext();

  const isHomepage = metadata.permalink === '/';
  const url = siteConfig.url.replace(/\/$/, '') + metadata.permalink;

  const graph = isHomepage
    ? homepageGraph
    : [
        {
          '@type': 'TechArticle',
          headline: metadata.title,
          description: metadata.description,
          url,
          // `lastUpdatedAt` is a millisecond timestamp in Docusaurus 3.x.
          ...(metadata.lastUpdatedAt
            ? {dateModified: new Date(metadata.lastUpdatedAt).toISOString()}
            : {}),
          author: {'@id': AUTHORS_ID},
          about: {'@id': SOFTWARE_ID},
          isPartOf: {
            '@type': 'WebSite',
            name: siteConfig.title,
            url: siteConfig.url,
          },
        },
        authors,
      ];

  return (
    <>
      <Head>
        <link
          rel="alternate"
          type="text/markdown"
          href={siteConfig.url.replace(/\/$/, '') + markdownUrl(metadata.source)}
        />
        <script type="application/ld+json">
          {JSON.stringify({'@context': 'https://schema.org', '@graph': graph})}
        </script>
      </Head>
      <Layout {...props} />
    </>
  );
}
