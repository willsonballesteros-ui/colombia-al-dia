import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { validateEdition, ensureUnique, readLedger, recordCompleted, sha256Mp4 } from './guard.mjs';

const edition = { brand: 'ORBIUNO', editionId: 'ORBIUNO_20261122_0800',
  approved: true, rightsConfirmed: true, approvedAt: '2026-11-22T12:00:00Z',
  mediaSha256: 'a'.repeat(64), accountId: 'authorized-account' };
const proof = { status: 'completed', publicationId: 'verified-publication',
  url: 'https://www.tiktok.com/@orbiuno.noticias/video/123456789' };

test('acepta edición vigente aprobada', () =>
  assert.equal(validateEdition(edition, new Date('2026-11-22T13:00:00Z')), edition));
test('bloquea edición vencida y sin derechos', () => {
  assert.throws(() => validateEdition(edition, new Date('2026-11-25T13:00:00Z')));
  assert.throws(() => validateEdition({ ...edition, rightsConfirmed: false }, new Date('2026-11-22T13:00:00Z')));
});
test('bloquea duplicados por edición y por contenido', () => {
  assert.throws(() => ensureUnique(edition, [edition]));
  assert.throws(() => ensureUnique(edition, [{ ...edition, editionId: 'DIFFERENT_ID' }]));
});
test('registra únicamente publicación comprobada, sin duplicados', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'tiktok-guard-'));
  try {
    const path = join(dir, 'ledger.json');
    assert.deepEqual(await readLedger(path), []);
    await assert.rejects(recordCompleted(path, edition, { ...proof, status: 'pending' }));
    await recordCompleted(path, edition, proof);
    assert.equal((await readLedger(path)).length, 1);
    await assert.rejects(recordCompleted(path, edition, proof), /registrado/);
    assert.equal((await readLedger(path)).length, 1);
    await writeFile(path, 'corrupt');
    await assert.rejects(readLedger(path));
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
test('rechaza archivos que no sean MP4', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'tiktok-mp4-'));
  try {
    const path = join(dir, 'bad.mp4');
    await writeFile(path, Buffer.alloc(2048));
    await assert.rejects(sha256Mp4(path), /MP4/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
