# Daily News

Personal morning briefing. A scheduled Claude routine researches the news and commits `site/data/YYYY-MM-DD.json` following `routine/PROMPT.md`. Cloudflare Pages serves `site/`. A Cloudflare cron worker triggers `send.yml`, which posts the briefing to Telegram at the configured time.

## Setup

1. Use this repo as a template, or fork it. Remove the previous reader's data:
   ```
   git rm -r site/data
   mkdir site/data && echo '[]' > site/data/index.json
   echo '{"last_sent": ""}' > state/sent.json
   git rm -r mockups
   ```
   `site/data/latest.json` is needed by the site once the first briefing exists.
2. Accounts and keys:
   - Telegram bot from @BotFather, and your chat id.
   - Pexels API key (free) for stock loop footage.
   - Cloudflare account (Pages project + Worker) and a GitHub token with `repo` + `workflow` scope on your copy.
3. GitHub repo secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PEXELS_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
4. Change the project-specific values:
   - `.github/workflows/deploy.yml`: `--project-name`
   - `cron/wrangler.toml`: `name`, `GITHUB_REPO`
   - `site/config.json`: `site_url`, send time, timezone, sections, voices
   - `routine/PROMPT.md`: the reader description on line 1, sections, languages, sources
5. Cloudflare environment:
   - Pages project: `SETTINGS_PASSWORD`, `GITHUB_TOKEN`, `GITHUB_REPO`
   - Worker (`cd cron && npx wrangler deploy`): `GITHUB_TOKEN`, deployed by `deploy-cron.yml` on push
6. `briefing.yml` runs Claude Code with `routine/PROMPT.md` each morning. Run `claude setup-token` locally and save the token as the repo secret `CLAUDE_CODE_OAUTH_TOKEN`.

Local runs: copy `.env.example` to `.env`.
