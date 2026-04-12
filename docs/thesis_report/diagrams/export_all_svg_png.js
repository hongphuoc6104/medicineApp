const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const DIAG   = __dirname;
const PNG    = path.join(__dirname, 'png');
const ASSETS = path.resolve(__dirname, '../assets/diagrams');

const items = [
  { svg: 'use_case.svg',           w: 900,  h: 620,  scale: 2 },
  { svg: 'architecture.svg',       w: 780,  h: 680,  scale: 2 },
  { svg: 'activity_create_plan.svg', w: 1020, h: 260, scale: 2 },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    headless: 'new',
  });

  for (const { svg: svgFile, w, h, scale } of items) {
    const svgPath = path.join(DIAG, 'svg', svgFile);
    const pngName = svgFile.replace('.svg', '.png');
    const pngPath = path.join(PNG, pngName);
    const assetPath = path.join(ASSETS, pngName);

    const svgContent = fs.readFileSync(svgPath, 'utf-8');
    const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgContent);

    const page = await browser.newPage();
    await page.setViewport({ width: w, height: h, deviceScaleFactor: scale });
    await page.goto(dataUrl, { waitUntil: 'networkidle0' });

    // Clip to exact SVG dimensions
    await page.screenshot({
      path: pngPath,
      clip: { x: 0, y: 0, width: w, height: h },
      type: 'png',
    });

    fs.copyFileSync(pngPath, assetPath);
    console.log(`OK: ${pngName}  (${w * scale} x ${h * scale})`);
    await page.close();
  }

  await browser.close();
  console.log('All done.');
})();
