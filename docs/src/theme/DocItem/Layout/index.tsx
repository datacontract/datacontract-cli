import React, {type ReactNode} from 'react';
import Head from '@docusaurus/Head';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme-original/DocItem/Layout';
import type LayoutType from '@theme/DocItem/Layout';
import type {WrapperProps} from '@docusaurus/types';

type Props = WrapperProps<typeof LayoutType>;

// Wraps the default doc layout to emit TechArticle JSON-LD on every doc page,
// giving AI answer engines machine-readable facts to attribute. The homepage is
// skipped because it carries SoftwareApplication structured data instead.
export default function LayoutWrapper(props: Props): ReactNode {
  const {metadata} = useDoc();
  const {siteConfig} = useDocusaurusContext();

  const isHomepage = metadata.permalink === '/';
  const url = siteConfig.url.replace(/\/$/, '') + metadata.permalink;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: metadata.title,
    description: metadata.description,
    url,
    ...(metadata.lastUpdatedAt
      ? {dateModified: new Date(metadata.lastUpdatedAt * 1000).toISOString()}
      : {}),
    author: {
      '@type': 'Organization',
      name: 'Data Contract CLI authors',
      url: 'https://datacontract.com',
    },
    isPartOf: {
      '@type': 'WebSite',
      name: siteConfig.title,
      url: siteConfig.url,
    },
  };

  return (
    <>
      {!isHomepage && (
        <Head>
          <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
        </Head>
      )}
      <Layout {...props} />
    </>
  );
}
