#!/usr/bin/env node
/**
 * Generates the command reference under `docs/docs/commands/` by running
 * `update_command_docs.py`, which renders the CLI's own `--help` output.
 *
 * Runs automatically before `npm run build` and `npm start` (see the `prebuild`
 * and `prestart` scripts in package.json). The pages are generated, never
 * committed (see .gitignore) — otherwise every pull request that touches a help
 * string would leave the committed copies stale.
 *
 * The generator is Python and needs the CLI importable, which the Node-only
 * Oryx container of Azure Static Web Apps cannot provide. The deploy workflow
 * therefore generates the pages before handing the site over, and if no
 * interpreter here can run the generator we keep the pages already on disk
 * instead of failing the deploy.
 */

import {spawnSync} from 'node:child_process';
import {existsSync, readdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(scriptDir, '..', '..');
const outputDir = path.join(repoRoot, 'docs', 'docs', 'commands');

// An activated virtualenv first, so the common case costs one process. `uv run`
// last: it bootstraps an environment on its own, which is what makes a fresh
// clone work, but it is the slow path.
const INTERPRETERS = [
  ['python3', ['update_command_docs.py']],
  ['python', ['update_command_docs.py']],
  ['uv', ['run', 'python', 'update_command_docs.py']],
];

/** The pages the generator would have written, if a previous run left them. */
function alreadyGenerated() {
  return existsSync(outputDir) && readdirSync(outputDir).some((entry) => entry.endsWith('.md'));
}

const attempts = [];
for (const [command, args] of INTERPRETERS) {
  // The generator resolves docs/docs/commands relative to the working directory.
  const result = spawnSync(command, args, {cwd: repoRoot, encoding: 'utf8'});
  if (result.status === 0) {
    process.stdout.write(result.stdout);
    console.log(`[command-docs] Generated docs/commands from the CLI --help output (via ${command}).`);
    process.exit(0);
  }
  attempts.push(`${command}: ${result.error ? result.error.message : (result.stderr || '').trim().split('\n').pop()}`);
}

if (alreadyGenerated()) {
  console.warn('[command-docs] Could not run update_command_docs.py — keeping the pages already in docs/commands.');
  for (const attempt of attempts) {
    console.warn(`[command-docs]   ${attempt}`);
  }
  process.exit(0);
}

console.error('[command-docs] Could not run update_command_docs.py and docs/commands is empty.');
for (const attempt of attempts) {
  console.error(`[command-docs]   ${attempt}`);
}
console.error('[command-docs] The command reference is rendered from the CLI, so it has to be installed:');
console.error("[command-docs]   uv pip install -e '.[dev]'   (see AGENTS.md)");
process.exit(1);
