export default {
  async scheduled(_event, env) {
    const res = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/send.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: 'application/vnd.github+json',
          'User-Agent': 'daily-news-cron',
        },
        body: JSON.stringify({ ref: 'main' }),
      },
    );
    if (res.status !== 204) throw new Error(`dispatch failed: ${res.status} ${await res.text()}`);
  },
};
