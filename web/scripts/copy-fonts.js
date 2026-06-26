/**
 * Stages the licensed Brandon Grotesque webfonts before `vite build`.
 *
 * Fontspring prohibits distributing the files with public source code, so
 * production receives them through Render Secret Files. Local development
 * may place them directly in web/public/fonts/.
 */
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

const SECRETS_DIR = '/etc/secrets';
const TARGET_DIR = join(process.cwd(), 'public', 'fonts');
const REQUIRED_FONTS = {
  'brandon-grotesque-medium.woff2': 26772,
  'brandon-grotesque-medium.woff': 34800,
  'brandon-grotesque-black.woff2': 20528,
  'brandon-grotesque-black.woff': 27024,
};

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

function isBrandonFont(file) {
  const lower = file.toLowerCase();
  return lower.includes('brandon') && (lower.endsWith('.woff2') || lower.endsWith('.woff'));
}

function removeStagedBrandonFonts() {
  if (!existsSync(TARGET_DIR)) return;
  for (const file of readdirSync(TARGET_DIR)) {
    if (!isBrandonFont(file)) continue;
    unlinkSync(join(TARGET_DIR, file));
    log(`removed previously staged ${file}`);
  }
}

function validateFontSizes() {
  const problems = [];

  for (const [file, expectedBytes] of Object.entries(REQUIRED_FONTS)) {
    const path = join(TARGET_DIR, file);
    if (!existsSync(path)) {
      problems.push(`${file} is missing`);
      continue;
    }

    const actualBytes = statSync(path).size;
    if (actualBytes !== expectedBytes) {
      problems.push(`${file} is ${actualBytes} bytes, expected ${expectedBytes} bytes`);
    }
  }

  return problems;
}

if (existsSync(SECRETS_DIR)) {
  const entries = readdirSync(SECRETS_DIR);
  mkdirSync(TARGET_DIR, { recursive: true });
  removeStagedBrandonFonts();

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

const fontProblems = validateFontSizes();
if (fontProblems.length > 0) {
  const message = `invalid Brandon Grotesque webfont files:\n- ${fontProblems.join('\n- ')}`;
  if (process.env.RENDER || existsSync(SECRETS_DIR)) {
    throw new Error(message);
  }
  log(`${message}; local build will use the CSS fallback`);
} else {
  log(`verified all ${Object.keys(REQUIRED_FONTS).length} required Brandon Grotesque files`);
}
