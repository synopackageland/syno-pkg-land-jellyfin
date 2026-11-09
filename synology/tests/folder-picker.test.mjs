import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {parse} from 'yaml';
import {
  renderSharedFolderScript, renderSharedFolderWizardFiles, sharedFolderInstallSteps,
} from '@synopackageland/cli/dist/standalone/shared-folder.js';
import {renderInstallWizardFiles} from '@synopackageland/cli/dist/build-spk/install-wizard.js';
import {folderPickerWizardFiles} from '@synopackageland/cli/dist/build-spk/folder-picker.js';

const manifest = parse(readFileSync(new URL('../dsm-package.yaml', import.meta.url), 'utf8'));
const folder = manifest.install.sharedFolder;
const key = folder.key;
const pkg = manifest.package;

function fixture(config, run) {
  const dir = mkdtempSync(join(tmpdir(), 'media-folders-'));
  try {
    const file = join(dir, 'config.json');
    writeFileSync(file, JSON.stringify(config) + '\n');
    return run(dir, file);
  } finally { rmSync(dir, {recursive: true, force: true}); }
}

function shell(script, dir, answers = {}) {
  const result = spawnSync('/bin/sh', ['-s'], {
    input: script, encoding: 'utf8',
    env: {PATH: process.env.PATH, SYNOPKG_PKGVAR: dir, SYNOPKG_PKGDEST: dir,
      SYNOPKG_PKG_STATUS: 'UPGRADE', ...answers},
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

const wizards = renderSharedFolderWizardFiles(pkg, folder);
function retained(config) {
  return fixture(config, dir => {
    const pages = JSON.parse(shell(wizards['upgrade_uifile.sh'], dir));
    const fields = pages.flatMap(page => page.items ?? []).flatMap(item => item.subitems ?? []);
    return Object.fromEntries(fields.map(field => [field.key, field.defaultValue]));
  });
}

test('legacy share-root upgrade prefills the original share without another choice', () => {
  const values = retained({schema: 1, shared_folders: {[key]: 'MediaLibrary'}});
  assert.equal(values[key], 'MediaLibrary');
  assert.equal(values[key + '_subpath'], '');
});

test('folder upgrade prefills a saved path two levels deep, including spaces', () => {
  const values = retained({schema: 1, shared_folders: {[key]: 'MediaLibrary'},
    shared_folder_paths: {[key]: 'Library/Level two'}});
  assert.equal(values[key], 'MediaLibrary');
  assert.equal(values[key + '_subpath'], 'Library/Level two');
});

test('postinst with omitted upgrade answers preserves the exact legacy record', () => {
  fixture({schema: 1, shared_folders: {[key]: 'MediaLibrary'}}, (dir, file) => {
    const before = readFileSync(file, 'utf8');
    shell(renderSharedFolderScript(pkg, folder), dir);
    assert.equal(readFileSync(file, 'utf8'), before);
  });
});

test('post-acquisition check failure does not fail installation or lose the selection', () => {
  fixture({schema: 1, shared_folders: {[key]: 'MediaLibrary'}}, (dir, file) => {
    shell(renderSharedFolderScript(pkg, folder), dir,
      {SYNOPKG_PKG_STATUS: 'INSTALL', [key]: 'MediaLibrary', [key + '_subpath']: 'Library/Level two'});
    assert.deepEqual(JSON.parse(readFileSync(file, 'utf8')), {
      schema: 1, shared_folders: {[key]: 'MediaLibrary'},
      shared_folder_paths: {[key]: 'Library/Level two'},
    });
  });
});

test('DSM 7.1 and 7.2.1 retain standard controls; modern dynamic wizard offers native chooser', () => {
  const install = renderInstallWizardFiles(pkg, sharedFolderInstallSteps(pkg, folder));
  const files = folderPickerWizardFiles(pkg, folder, {...install.static, ...install.dynamic});
  const standard = JSON.parse(files.install_uifile);
  assert.ok(standard.some(page => page.items.some(item => item.type === 'combobox')));
  assert.ok(standard.some(page => page.items.some(item => item.subitems?.some(f => f.key === key + '_subpath'))));
  assert.doesNotMatch(files.install_uifile, /custom_render_fn/);
  assert.match(files['install_uifile.sh'], /micro:-0.*-ge 2/);
  assert.match(files['install_uifile.sh'], /custom_render_fn/);
  for (const [version, native] of [
    ['majorversion=7\nminorversion=1\nmicro=1\n', false],
    ['majorversion=7\nminorversion=2\nmicro=1\n', false],
    ['majorversion=7\nminorversion=2\nmicro=2\n', true],
    ['majorversion=7\nminorversion=3\nmicro=2\n', true],
    ['', false],
  ]) {
    fixture({schema: 1, shared_folders: {[key]: 'MediaLibrary'}}, dir => {
      const versionFile = join(dir, 'VERSION');
      writeFileSync(versionFile, version);
      const script = files['install_uifile.sh'].replaceAll('/etc/VERSION', versionFile);
      const pages = JSON.parse(shell(script, dir, {SYNOPKG_PKG_STATUS: 'INSTALL'}));
      assert.equal(pages.some(page => typeof page.custom_render_fn === 'string'), native, version);
    });
  }
});
