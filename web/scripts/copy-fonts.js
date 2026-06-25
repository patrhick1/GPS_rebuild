/**
 * Stages the licensed Brandon Grotesque webfonts before `vite build`.
 *
 * Fontspring prohibits distributing the files with public source code, so
 * production receives them through Render Secret Files. Local development
 * may place them directly in web/public/fonts/.
 */
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SECRETS_DIR = '/etc/secrets';
const TARGET_DIR = join(process.cwd(), 'public', 'fonts');
const REQUIRED_FONTS = [
  'brandon-grotesque-medium.woff2',
  'brandon-grotesque-medium.woff',
  'brandon-grotesque-black.woff2',
  'brandon-grotesque-black.woff',
];

function log(message) {
  process.stdout.write(`[copy-fonts] ${message}\n`);
}

function normalizedName(file) {
  const lower = file.toLowerCase();
  const extension = lower.endsWith('.woff2') ? '.woff2' : lower.endsWith('.woff') ? '.woff' : null;
  if (!extension) return null;
  if (lower.includes('brandongrotesque-medium') || lower.includes('brandon-grotesque-medium')) {
    return `brandon-grotesque-medium${extension}`;
  }
  if (lower.includes('brandongrotesque-black') || lower.includes('brandon-grotesque-black')) {
    return `brandon-grotesque-black${extension}`;
  }
  return null;
}

if (existsSync(SECRETS_DIR)) {
  const entries = readdirSync(SECRETS_DIR);
  mkdirSync(TARGET_DIR, { recursive: true });

  for (const file of entries) {
    const source = join(SECRETS_DIR, file);
    if (!statSync(source).isFile()) continue;
    const targetName = normalizedName(file);
    if (!targetName) continue;
    copyFileSync(source, join(TARGET_DIR, targetName));
    log(`staged ${file} as ${targetName}`);
  }
} else {
  log('no /etc/secrets/ found - checking local public/fonts');
}

const missing = REQUIRED_FONTS.filter((file) => !existsSync(join(TARGET_DIR, file)));
if (missing.length > 0) {
  const message = `missing required Brandon Grotesque files: ${missing.join(', ')}`;
  if (process.env.RENDER || existsSync(SECRETS_DIR)) {
    throw new Error(message);
  }
  log(`${message}; local build will use the CSS fallback`);
} else {
  log(`verified all ${REQUIRED_FONTS.length} required Brandon Grotesque files`);
}
