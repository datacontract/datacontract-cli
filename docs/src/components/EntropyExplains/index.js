import React, {useState} from 'react';
import {useLocation} from '@docusaurus/router';
import styles from './styles.module.css';

// "Entropy Explains": two-minute explainer videos with slides, https://www.entropy-data.com/learn/entropy-explains
// <EntropyExplainsVideo episode="data-quality" /> shows a click-to-play video: the slide image until someone clicks
// play, so nothing is loaded from YouTube before that (no cookies, no extra page weight), and each play is tracked
// in Umami as "play-entropy-explains". <EntropyExplainsLink episode="..." /> is the one-line variant.
// Both link to the episode page on entropy-data.com (slides and video) with UTM parameters.
const EPISODES = {
  'data-contracts': {n: 1, youtube: 'agUJ5gqBTtk', image: '01-data-contracts.png', title: 'Data Contracts'},
  'data-products': {n: 2, youtube: 'np_U1lowwoc', image: '02-data-products.png', title: 'Data Contracts and Data Products'},
  'semantics': {n: 3, youtube: 'roXo8AU0yWA', image: '03-semantics.png', title: 'Data Contracts and Semantics'},
  'building-with-ai': {n: 4, youtube: 'dq72KvRs7OA', image: '04-building-with-ai.png', title: 'Building Data Products with AI'},
  'under-contract': {n: 5, youtube: 'eXrH1BCgyBI', image: '05-under-contract.png', title: 'Put Your Data Under Contract'},
  'ci-cd': {n: 6, youtube: 'W3bBe-yFvXo', image: '06-ci-cd.png', title: 'Data Contracts and CI/CD'},
  'data-quality': {n: 9, youtube: 'qkC6nw4KzzI', image: '09-data-quality.png', title: 'Data Contracts and Data Quality'},
  'dbt': {n: 10, youtube: 'Ms73kS1OkV4', image: '10-dbt.png', title: 'Data Contracts with dbt'},
};

function useEpisode(episode) {
  const e = EPISODES[episode];
  if (!e) throw new Error(`Unknown Entropy Explains episode: ${episode}`);
  const {pathname} = useLocation();
  const page = pathname.replace(/\/$/, '') || '/';
  const url = `https://www.entropy-data.com/learn/entropy-explains-${episode}` +
    `?utm_source=cli.datacontract.com&utm_medium=referral&utm_content=${encodeURIComponent(page)}`;
  return {...e, url, page};
}

export function EntropyExplainsVideo({episode}) {
  const e = useEpisode(episode);
  const [playing, setPlaying] = useState(false);
  const play = () => {
    setPlaying(true);
    window.umami?.track('play-entropy-explains', {episode, page: e.page});
  };
  return (
    <figure className={styles.video}>
      <div className={styles.frame}>
        {playing ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${e.youtube}?autoplay=1&rel=0`}
            title={`${e.title}, Explained in 2 Minutes`}
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
          />
        ) : (
          <button type="button" className={styles.poster} onClick={play} aria-label={`Play: ${e.title}, Explained in 2 Minutes`}>
            <img src={`https://www.entropy-data.com/media/entropy-explains/${e.image}`} alt="" loading="lazy" width="1280" height="720" />
            <span className={styles.play} aria-hidden="true" />
          </button>
        )}
      </div>
      <figcaption>
        <strong>{e.title}, explained in 2 minutes.</strong>{' '}
        <a href={e.url}>Entropy Explains #{e.n}: slides and video</a>
      </figcaption>
    </figure>
  );
}

export function EntropyExplainsLink({episode}) {
  const e = useEpisode(episode);
  return (
    <p className={styles.link}>
      ▶ <strong>Explained in 2 minutes:</strong> <a href={e.url}>{e.title}</a> · Entropy Explains #{e.n}
    </p>
  );
}
