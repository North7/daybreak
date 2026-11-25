// 2026-11-25 回覆／長文小幫手即時讀運營資料（Cloudflare Pages Function，網址 /ops-live/<倉庫裡的路徑>）。
// 為什麼：運營每推一次回覆或長文（一天約 30 次）原本都要整站重新部署，小幫手才讀得到新的 data/replies.json，
// 一個月約 900 分鐘 Actions；倉庫改私有後要算額度。現在這些推送不部署（cloudflare.yml 的 paths-ignore），小幫手改從這裡讀 GitHub 上 main 的最新版。
// 讀法：
//   - Cloudflare Pages 專案設了 GH_READ_TOKEN（GitHub fine-grained token，只給 North7/daybreak 的 Contents: Read-only）→ 走 GitHub API，即時、私有庫也能讀
//   - 沒設 → raw.githubusercontent.com（只有公開庫能讀，GitHub 會快取最多 5 分鐘）
// 只開放下面這幾類檔案；其他路徑一律 404。小幫手讀 JSON 失敗會退回網站上部署的那份（ops/app/app.js）。
const ALLOW = [
  /^data\/(replies|longposts|flash)\.json$/,
  /^data\/(replies|longposts|flash)\/[\w.\-]+\.(png|jpe?g|gif|webp|mp4)$/,
];
const TYPES = { json: 'application/json; charset=utf-8', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp', mp4: 'video/mp4' };

export async function onRequestGet({ params, env }) {
  const p = [].concat(params.path || []).join('/');
  if (!ALLOW.some((r) => r.test(p))) return new Response('not found', { status: 404 });
  const repo = env.GH_REPO || 'North7/daybreak';
  const tok = env.GH_READ_TOKEN;
  const up = tok
    ? await fetch(`https://api.github.com/repos/${repo}/contents/${p}?ref=main`, {
        headers: { Authorization: `Bearer ${tok}`, Accept: 'application/vnd.github.raw', 'User-Agent': 'daybreak-ops-live', 'X-GitHub-Api-Version': '2022-11-28' },
      })
    : await fetch(`https://raw.githubusercontent.com/${repo}/main/${p}`);
  if (!up.ok) return new Response('upstream ' + up.status, { status: up.status === 404 ? 404 : 502 });
  return new Response(up.body, {
    headers: {
      'Content-Type': TYPES[p.split('.').pop().toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-store',
      'X-Ops-Live': tok ? 'api' : 'raw',
    },
  });
}
