import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  managedInstall,
  mayApplyUpdate,
  installerArguments,
  APP_ID,
} from '../src/main/launcher/install-policy';
test('automatic install requires the fixed per-user location and app marker', () => {
  const root = 'C:\\Users\\Player\\AppData\\Local';
  const executable = root + '\\Programs\\AtlasLauncher\\AtlasLauncher.exe';
  assert.equal(managedInstall(executable, root, { appId: APP_ID }), true);
  assert.equal(managedInstall(executable.toUpperCase(), root, { appId: APP_ID }), true);
  for (const path of [
    'C:\\Downloads\\AtlasLauncher.exe',
    root + '\\Programs\\Other\\AtlasLauncher.exe',
    executable + '.other',
  ])
    assert.equal(managedInstall(path, root, { appId: APP_ID }), false);
  assert.equal(managedInstall(executable, root, {}), false);
  assert.equal(managedInstall(executable, undefined, { appId: APP_ID }), false);
});
test('updates apply only after verified download with the game and operations stopped', () => {
  assert.equal(mayApplyUpdate(true, true, false, false), true);
  for (const args of [
    [false, true, false, false],
    [true, false, false, false],
    [true, true, true, false],
    [true, true, false, true],
  ])
    assert.equal(mayApplyUpdate(...(args as [boolean, boolean, boolean, boolean])), false);
});
test('installer args are fixed flags with a validated PID, without a shell or user-controlled command', () => {
  assert.deepEqual(installerArguments(1234, false), ['/S', '/PARENT_PID=1234']);
  assert.deepEqual(installerArguments(1234, true), ['/S', '/PARENT_PID=1234', '/RESTART=1']);
  for (const pid of [0, -1, NaN, Infinity, 1.5])
    assert.throws(() => installerArguments(pid, false));
});
