import assert from 'node:assert/strict';
import { execFile, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { test } from 'node:test';
import { advance, checkManifest, get, openLedger, promotionEligibility, rankPosts, reserve, withVerifiedVideo } from './distribution.mjs';

const account = '_0002Srdx8vdogbZfAfLEtY1F2BmuPSX6F26';
const now = new Date('2026-11-28T14:00:00Z');
const edition = 'ORBIUNO-2026-11-28-0800';
const manifest = {
  editionId: edition, brand: 'ORBIUNO', accountId: account, localTime: '2026-11-28T08:00:00-05:00',
  approved: true, approvedAt: '2026-11-28T13:05:00Z', rightsConfirmed: true,
  rights: { status: 'cleared', platform: 'tiktok', evidence: 'Simulación de licencia' },
  videoUrl: 'https://colombia-al-dia.pages.dev/media/2026-11-28/ORBIUNO_2026-11-28_0800_6_NOTICIAS.mp4',
  mediaSha256: 'a'.repeat(64), size: 2048, duration: 1, caption: 'Texto de prueba',
  credits: Array(6).fill('Crédito de prueba'), sources: Array(6).fill('Fuente de prueba'),
};

async function temp(t) {
  const dir = await mkdtemp(join(tmpdir(), 'distribution-test-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  return dir;
}

test('rechaza derechos, aprobaciones, cuenta, fecha o marca incorrectas', () => {
  for (const change of [{ rights: {} }, { approved: false }, { accountId: 'other' },
    { brand: 'MYCAR' }, { localTime: '2026-11-28T17:00:00-05:00' }, { sources: [] }]) {
    assert.throws(() => checkManifest({ ...manifest, ...change }, account, now));
  }
});

test('valida el MP4 original y rechaza enlace vencido, HTML, tamaño incorrecto y hash distinto', async t => {
  const path = join(await temp(t), 'fixture.mp4');
  execFileSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=s=32x32:r=10:d=1',
    '-f', 'lavfi', '-i', 'anullsrc', '-t', '1', '-c:v', 'libx264', '-c:a', 'aac', path]);
  const bytes = await readFile(path);
  const spec = { ...manifest, size: bytes.length, mediaSha256: createHash('sha256').update(bytes).digest('hex') };
  const video = (body, status = 200, type = 'video/mp4') => ({
    now, fetchVideo: async () => new Response(body, { status, headers: { 'content-type': type } }),
  });
  await withVerifiedVideo(spec, account, async file => assert.deepEqual(await readFile(file), bytes), video(bytes));
  for (const [options, error] of [
    [video('expired', 403), /403/],
    [video('<html>', 200, 'text/html'), /MP4 no disponible/],
    [video(bytes.subarray(0, -1)), /incompleto/],
    [video(Buffer.concat([bytes, Buffer.alloc(1)])), /excede/],
    [video(Buffer.alloc(bytes.length)), /Cabecera/],
    [video(Buffer.concat([bytes.subarray(0, -1), Buffer.from([bytes.at(-1) ^ 1])])), /SHA-256/],
  ]) await assert.rejects(withVerifiedVideo(spec, account, () => assert.fail(), options), error);
});

test('reserva en procesos simultáneos y concilia tras reabrir sin volver a enviar', async t => {
  const dir = await temp(t);
  const path = join(dir, 'durable.sqlite');
  const db = openLedger(path);
  db.close();
  const module = new URL('./distribution.mjs', import.meta.url).href;
  const worker = join(dir, 'reserve.mjs');
  await writeFile(worker, `import { openLedger, reserve } from ${JSON.stringify(module)};
    reserve(openLedger(process.argv[2]), ${JSON.stringify(manifest)}, ${JSON.stringify(account)}, new Date(${+now}));`);
  const run = promisify(execFile);
  const executions = await Promise.allSettled([run(process.execPath, [worker, path]), run(process.execPath, [worker, path])]);
  assert.deepEqual(executions.map(result => result.status).sort(), ['fulfilled', 'rejected']);
  let ledger = openLedger(path);
  const proof = { reference: 'respuesta simulada', postId: 'post', publicationId: 'destination', revision: 'revision' };
  assert.throws(() => reserve(ledger, { ...manifest, mediaSha256: 'b'.repeat(64) }, account, now), /UNIQUE/);
  advance(ledger, edition, 0, 'validated', proof);
  advance(ledger, edition, 1, 'uploaded', proof);
  advance(ledger, edition, 2, 'draft', proof);
  assert.throws(() => advance(ledger, edition, 3, 'approved', proof), /aprobación/);
  advance(ledger, edition, 3, 'approved', { ...proof, ownerApproved: true });
  assert.throws(() => advance(ledger, edition, 4, 'submitted', proof), /historial/);
  advance(ledger, edition, 4, 'submitted', { ...proof, accountId: account, canPublish: true, historyChecked: true });
  ledger.close();
  ledger = openLedger(path);
  t.after(() => ledger.close());
  assert.equal(get(ledger, edition).state, 'submitted');
  assert.throws(() => advance(ledger, edition, 4, 'submitted', proof), /transición/);
  advance(ledger, edition, 5, 'reconciliation_required', { reference: 'timeout' });
  assert.throws(() => advance(ledger, edition, 6, 'submitted', proof), /transición/);
  advance(ledger, edition, 6, 'completed', { ...proof, url: 'https://www.tiktok.com/@orbiuno.noticias/video/123' });
  assert.equal(get(ledger, edition).state, 'completed');
  assert.equal(JSON.parse(get(ledger, edition).evidence).reconciliation_required.reference, 'timeout');
});

test('calcula 168 horas desde la última promoción y evita piezas repetidas', () => {
  const history = { complete: true, promotions: [{ verified: true, id: 'post', publishedAt: '2026-11-22T15:00:00Z' }] };
  assert.deepEqual(promotionEligibility(history, now), { eligible: false, nextEligibleAt: '2026-11-29T15:00:00.000Z' });
  assert.throws(() => promotionEligibility({ ...history, complete: false }, now), /incompleto/);
  const base = { relevant: true, publishedAt: '2026-11-27T20:00:00Z', reach: 100, views: 150 };
  assert.deepEqual(rankPosts([{ ...base, id: 0, alreadyPromoted: true }, { ...base, id: 1 },
    { ...base, id: 2, shares: 5 }], now).map(post => post.id), [2, 1]);
});
