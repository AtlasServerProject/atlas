import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chooseGameMemory, memoryStatus } from '../src/main/installation/memory';
const GB = 1024 ** 3;
test('launch adjusts heap to available memory instead of rejecting a high preference', () => {
  const value = chooseGameMemory(8192, 16 * GB, 6 * GB);
  assert.equal(value.heapMb, 5120);
  assert.equal(value.adjusted, true);
  assert.equal(value.heapMb + 1024, value.availableMb);
});
test('launch preserves a reasonable request and leaves memory for the system', () => {
  assert.equal(chooseGameMemory(4096, 16 * GB, 8 * GB).heapMb, 4096);
  assert.equal(chooseGameMemory(8192, 8 * GB, 8 * GB).heapMb, 6144);
  assert.equal(chooseGameMemory(8192, 16 * GB, 5 * GB).heapMb, 4096);
});
test('less than 4 GB requested or available no longer blocks launch', () => {
  assert.equal(chooseGameMemory(2048, 16 * GB, 8 * GB).heapMb, 2048);
  assert.equal(chooseGameMemory(4096, 4 * GB, 3 * GB).heapMb, 2048);
  assert.equal(chooseGameMemory(4096, 2 * GB, 1 * GB).heapMb, 512);
  assert.equal(chooseGameMemory(8192, 16 * GB, 1.9 * GB).heapMb, 768);
  assert.equal(memoryStatus(16 * GB, 1.9 * GB).recommendedMb, 0);
  assert.equal(memoryStatus(16 * GB, 8 * GB).recommendedMb, 6144);
});
test('even scarce free RAM allows an attempt; only invalid heap values are rejected', () => {
  assert.equal(chooseGameMemory(4096, 4 * GB, 0.1 * GB).heapMb, 512);
  assert.equal(chooseGameMemory(512, 2 * GB, 0).heapMb, 512);
  for (const value of [0, 511, -1, 1024.5, Number.NaN, Number.POSITIVE_INFINITY, 32769])
    assert.throws(() => chooseGameMemory(value, 16 * GB, 8 * GB), /válido/);
});
