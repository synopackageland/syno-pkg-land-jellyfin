#!/usr/bin/env node
// Use the CLI's existing OCI registry resolver; never build or publish an image.
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
const [tag] = process.argv.slice(2);
const match = /^v?((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?)$/.exec(tag ?? '');
if (!match) throw new Error('Use the selected stable upstream tag.');
const config = JSON.parse(readFileSync(new URL('./upstream-recipe.json', import.meta.url), 'utf8'));
if (config.kind !== 'official-image' || !['tag', 'version'].includes(config.imageTag)) throw new Error('Invalid official image recipe.');
const imageTag = config.imageTag === 'version' ? match[1] : tag;
const reference = `${config.repository}:${imageTag}`;
const temp = mkdtempSync(join(tmpdir(), 'synopkgland-image-pin-'));
try {
  // images pin edits only compose.yaml; use a bounded temporary project so the
  // App's base Compose and upstream source remain unchanged on lookup failure.
  writeFileSync(join(temp, 'dsm-package.yaml'), 'schema: 2\n');
  writeFileSync(join(temp, 'compose.yaml'), JSON.stringify({services: {[config.service]: {image: reference}}}, null, 2) + '\n');
  const result = spawnSync('synopkgland', ['--project', temp, 'images', 'pin'], {stdio: 'inherit'});
  if (result.error || result.status !== 0) throw new Error('Official image digest lookup failed; no Compose override was changed.');
  const pinned = JSON.parse(readFileSync(join(temp, 'compose.yaml'), 'utf8'));
  const image = pinned.services[config.service].image;
  if (!image.startsWith(`${reference}@sha256:`) || !/@sha256:[0-9a-f]{64}$/.test(image)) throw new Error('Registry lookup did not produce the selected tag plus digest.');
  writeFileSync(new URL('./compose.image.yaml', import.meta.url), JSON.stringify(pinned, null, 2) + '\n');
} finally {rmSync(temp, {recursive: true, force: true});}
