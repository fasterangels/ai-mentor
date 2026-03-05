#!/usr/bin/env node
const fs = require('fs');
const args = process.argv.slice(2);
function getArg(name) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : null;
}
const version = getArg('--version') || '0.0.0';
const tag = getArg('--tag') || 'v' + version;
const nsisSigPath = getArg('--nsis-sig');
const outPath = getArg('--out');
if (!nsisSigPath || !outPath) {
  console.error('Usage: node generate-latest-json.js --version VER --tag TAG --nsis-sig PATH --out OUT');
  process.exit(1);
}
const sigContent = fs.readFileSync(nsisSigPath, 'utf-8').trim();
const baseUrl = 'https://github.com/fasterangels/ai-mentor/releases/download';
const exeName = 'AI-Mentor-' + version + '-x64-setup.exe';
const manifest = {
  version,
  notes: '',
  pub_date: new Date().toISOString(),
  platforms: {
    'windows-x86_64': {
      signature: sigContent,
      url: baseUrl + '/' + tag + '/' + exeName,
    },
  },
};
fs.writeFileSync(outPath, JSON.stringify(manifest, null, 2), 'utf-8');
console.log('Wrote', outPath);
