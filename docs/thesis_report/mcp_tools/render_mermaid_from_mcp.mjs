import fs from 'node:fs/promises';
import path from 'node:path';
import { generateMermaidInkUrl } from 'mcp-mermaid-img';

const root = '/home/hongphuoc/Desktop/medicineApp/docs/thesis_report';
const sourceDir = path.join(root, 'diagrams');
const outputDir = path.join(root, 'assets', 'diagrams');

const files = [
  'architecture.mmd',
  'scan_flow.mmd',
  'use_case.mmd',
  'activity_create_plan.mmd',
  'sequence_scan.mmd',
  'erd_main.mmd',
];

await fs.mkdir(outputDir, { recursive: true });

for (const file of files) {
  const inputPath = path.join(sourceDir, file);
  const source = await fs.readFile(inputPath, 'utf8');
  const url = generateMermaidInkUrl(source, {
    type: 'svg',
    theme: 'neutral',
    bgColor: '!white',
  });

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${file}: ${response.status} ${response.statusText}`);
  }

  const svg = await response.text();
  const outName = file.replace(/\.mmd$/, '.svg');
  const outPath = path.join(outputDir, outName);
  await fs.writeFile(outPath, svg, 'utf8');
  console.log(`Rendered ${outName}`);
}
