const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export async function onRequest({ request, env, next }) {
  const url = new URL(request.url);
  const id = url.searchParams.get('a');
  const res = await next();
  if (!id) return res;

  const d = /^[\d-]+$/.test(url.searchParams.get('d') || '') ? url.searchParams.get('d') : 'latest';
  let item;
  try {
    const r = await env.ASSETS.fetch(new URL(`/data/${d}.json`, url));
    item = (await r.json()).items.find((i) => String(i.id) === id);
  } catch {
    return res;
  }
  if (!item) return res;

  const x = (url.searchParams.get('l') === 'it' && item.i18n && item.i18n.it) || item;
  const img = (item.media || []).find((m) => m.type === 'image');
  const meta =
    `<meta property="og:type" content="article"><meta property="og:title" content="${esc(x.title)}">` +
    `<meta property="og:description" content="${esc(x.summary)}"><meta property="og:site_name" content="Daily News">` +
    (img ? `<meta property="og:image" content="${esc(img.u)}"><meta name="twitter:card" content="summary_large_image">` : '') +
    `<meta name="twitter:title" content="${esc(x.title)}"><meta name="twitter:description" content="${esc(x.summary)}">`;
  return new HTMLRewriter()
    .on('title', { element: (e) => e.setInnerContent(x.title) })
    .on('head', { element: (e) => e.append(meta, { html: true }) })
    .transform(res);
}
