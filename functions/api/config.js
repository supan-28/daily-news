const SECTIONS = ['ita', 'reg', 'ai', 'pol', 'inn', 'biz', 'lav', 'vc', 'cr7'];
const ZONES = ['Europe/Rome', 'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Madrid', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Asia/Dubai', 'Asia/Tokyo', 'UTC'];
const VOICES = ['it-IT-GiuseppeMultilingualNeural', 'it-IT-IsabellaNeural', 'it-IT-ElsaNeural', 'it-IT-DiegoNeural', 'en-GB-SoniaNeural', 'en-GB-RyanNeural', 'en-US-AvaMultilingualNeural', 'en-US-EmmaMultilingualNeural', 'en-US-AndrewMultilingualNeural', 'en-US-BrianMultilingualNeural', 'en-US-AriaNeural'];
const PATH = 'site/config.json';

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

async function sha256(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid request' }, 400);
  }
  if ((await sha256(String(body.password || ''))) !== (await sha256(env.SETTINGS_PASSWORD || '\0'))) {
    return json({ error: 'Wrong password' }, 401);
  }
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(body.send_time || '')) return json({ error: 'Invalid time' }, 400);
  if (!ZONES.includes(body.timezone)) return json({ error: 'Invalid time zone' }, 400);

  const api = `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${PATH}`;
  const headers = {
    authorization: `Bearer ${env.GITHUB_TOKEN}`,
    'user-agent': 'daily-news-settings',
    accept: 'application/vnd.github+json',
  };
  const cur = await fetch(api, { headers });
  if (!cur.ok) return json({ error: 'Could not read current config' }, 502);
  const file = await cur.json();
  const old = JSON.parse(atob(file.content.replace(/\n/g, '')));

  const next = {
    send_time: body.send_time,
    timezone: body.timezone,
    telegram_enabled: !!body.telegram_enabled,
    telegram_language: body.telegram_language === 'it' ? 'it' : 'en',
    voice_it: VOICES.includes(body.voice_it) ? body.voice_it : old.voice_it,
    voice_en: VOICES.includes(body.voice_en) ? body.voice_en : old.voice_en,
    site_url: old.site_url,
    sections: Object.fromEntries(SECTIONS.map((s) => [s, !!(body.sections || {})[s]])),
  };
  const put = await fetch(api, {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      message: 'Update settings',
      sha: file.sha,
      content: btoa(JSON.stringify(next, null, 2) + '\n'),
    }),
  });
  if (!put.ok) return json({ error: 'Could not save' }, 502);
  return json({ ok: true });
}
