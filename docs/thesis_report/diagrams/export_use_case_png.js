const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const SVG_PATH = path.resolve(__dirname, 'svg/use_case.svg');
const PNG_OUT  = path.resolve(__dirname, 'png/use_case.png');
const ASSETS_PNG = path.resolve(__dirname, '../assets/diagrams/use_case.png');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    headless: 'new'
  });

  const page = await browser.newPage();

  // Load SVG as data URL
  const svgContent = fs.readFileSync(SVG_PATH, 'utf-8');
  const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgContent);

  await page.goto(dataUrl, { waitUntil: 'networkidle0' });

  // Set viewport to match SVG dimensions (900 x 620) * 2x for retina
  await page.setViewport({ width: 900, height: 620, deviceScaleFactor: 2 });

  await page.screenshot({
    path: PNG_OUT,
    fullPage: true,
    type: 'png',
  });

  // Copy to assets
  fs.copyFileSync(PNG_OUT, ASSETS_PNG);

  await browser.close();
  console.log('PNG written:', PNG_OUT);
  console.log('PNG copy:  ', ASSETS_PNG);
})();
