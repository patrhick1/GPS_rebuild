/**
 * Copies licensed webfont files into public/fonts/ before `vite build`.
 *
 * The Fontspring EULA prohibits redistributing Brandon Grotesque with
 * public source code, so the actual .woff2/.woff files are kept out of
 * the repo (see .gitignore). On Render, we mount them via Secret Files
 * (/etc/secrets/*) and this prebuild step stages them where Vite picks
 * them up for the static bundle.
 *
 * Local development: drop the .woff2/.woff files in web/public/fonts/
 * by hand. This script is a no-op when /etc/secrets/ doesn't exist.
 */
import { existsSync, mkdirSync, readdirSync, copyFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SECRETS_DIR = '/etc/secrets';
const TARGET_DIR = join(process.cwd(), 'public', 'fonts');

function log(msg) {
  process.stdout.write(`[copy-fonts] ${msg}\n`);
}

if (!existsSync(SECRETS_DIR)) {
  log('no /etc/secrets/ found — assuming local dev, skipping');
  process.exit(0);
}

let entries;
try {
  entries = readdirSync(SECRETS_DIR);
} catch (err) {
  log(`could not read ${SECRETS_DIR}: ${err.message}`);
  process.exit(0);
}

const fonts = entries.filter(
  (name) =>
    (name.endsWith('.woff2') || name.endsWith('.woff')) &&
    statSync(join(SECRETS_DIR, name)).isFile(),
);

if (fonts.length === 0) {
  log(`no .woff2/.woff files in ${SECRETS_DIR}; skipping`);
  process.exit(0);
}

mkdirSync(TARGET_DIR, { recursive: true });

for (const file of fonts) {
  copyFileSync(join(SECRETS_DIR, file), join(TARGET_DIR, file));
}

log(`copied ${fonts.length} font file(s) into ${TARGET_DIR}`);
