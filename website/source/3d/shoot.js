const { chromium } = require('playwright');
const DIR = __dirname;
const jobs = JSON.parse(process.argv[2]);
(async () => {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const j of jobs) {
    const p = await b.newPage({ viewport: { width: j.w, height: j.h } });
    p.on('console', m => { if (m.type() === 'error') console.log('ERR', m.text()); });
    p.on('pageerror', e => console.log('PAGEERR', e.message));
    await p.route('http://local/**', async r => { const u = new URL(r.request().url()); const f = require('path').join(DIR, decodeURIComponent(u.pathname));
      const ct = f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : f.endsWith('.json') ? 'application/json' : 'application/octet-stream';
      try { await r.fulfill({ body: require('fs').readFileSync(f), contentType: ct }); } catch (e) { await r.fulfill({ status: 404 }); } });
    await p.goto(`http://local/scene.html?` + new URLSearchParams(j.q || {}).toString() + `&w=${j.w}&h=${j.h}`);
    await p.waitForFunction(() => window.DONE === true, null, { timeout: 180000 });
    const anch = await p.evaluate(() => window.ANCH); require('fs').writeFileSync(j.out + '.json', JSON.stringify(anch));
    await p.screenshot({ path: j.out, omitBackground: !(j.q && j.q.bg) });
    console.log('ok', j.out); await p.close();
  }
  await b.close();
})();
