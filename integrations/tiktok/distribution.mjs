import { execFile } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { mkdtemp, rm, stat, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Transform, Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { DatabaseSync } from 'node:sqlite';
import { promisify } from 'node:util';
import { sha256Mp4, validateEdition } from './guard.mjs';

const probe = promisify(execFile);
const maxBytes = 25 * 1024 ** 2;
const origins = new Set(['https://colombia-al-dia.pages.dev', 'https://busco-autos.pages.dev']);
const orbiunoAccount = '_0002Srdx8vdogbZfAfLEtY1F2BmuPSX6F26';
const historicalOrbiuno = new Set(['ORBIUNO-2026-11-20-0800', 'ORBIUNO-2026-11-27-1800']);
const transitions = {
  pending: ['validated'],
  validated: ['uploaded', 'reconciliation_required'],
  uploaded: ['draft', 'reconciliation_required'],
  draft: ['approved'],
  approved: ['submitted'],
  submitted: ['processing', 'completed', 'failed', 'reconciliation_required'],
  processing: ['completed', 'failed', 'reconciliation_required'],
  reconciliation_required: ['uploaded', 'draft', 'processing', 'completed', 'failed'],
  completed: [],
  failed: [],
};

function assert(condition, error) {
  if (!condition) throw new Error(error);
}

export function checkManifest(manifest, expectedAccount, now = new Date()) {
  validateEdition(manifest, now);
  const { brand, editionId, localTime, videoUrl, size, duration, caption, sources, credits, rights, accountId } = manifest;
  assert(/^\d{4}-\d{2}-\d{2}T(?:08|18):00:00-05:00$/.test(localTime) &&
    Number.isFinite(Date.parse(localTime)) &&
    new Date(localTime).toISOString().slice(0, 10) === localTime.slice(0, 10) &&
    Date.parse(localTime) <= now.getTime() &&
    Date.parse(manifest.approvedAt) >= Date.parse(localTime) &&
    now.getTime() - Date.parse(localTime) <= 36 * 3600_000, 'Fecha o franja inválida');
  const date = localTime.slice(0, 10);
  const slot = localTime.slice(11, 16).replace(':', '');
  assert(editionId === `${brand}-${date}-${slot}`, 'Edición no corresponde a la marca o franja');
  assert(expectedAccount && accountId === expectedAccount &&
    (brand === 'ORBIUNO' ? accountId === orbiunoAccount : accountId !== orbiunoAccount), 'Destino incorrecto');
  const url = new URL(videoUrl);
  assert(origins.has(url.origin) && !url.username && !url.password && !url.search && !url.hash &&
    url.pathname.startsWith(`/media/${date}/`) &&
    url.pathname.endsWith(`/${brand}_${date}_${slot}_${brand === 'ORBIUNO' ? 6 : 5}_NOTICIAS.mp4`),
  'URL no corresponde al original de la edición');
  assert(Number.isInteger(size) && size >= 1024 && size <= maxBytes &&
    typeof duration === 'number' && Number.isFinite(duration) && duration > 0, 'Tamaño o duración inválidos');
  assert(typeof caption === 'string' && caption.trim() &&
    [sources, credits].every(items => Array.isArray(items) &&
      items.length >= (brand === 'ORBIUNO' ? 6 : 5) &&
      items.every(item => typeof item === 'string' && item.trim())), 'Faltan texto, fuentes o créditos');
  assert(rights?.status === 'cleared' && rights.platform === 'tiktok' &&
    typeof rights.evidence === 'string' && rights.evidence.trim(), 'Falta evidencia de derechos TikTok');
  return manifest;
}

export async function withVerifiedVideo(manifest, expectedAccount, useVideo, { fetchVideo = fetch, now = new Date() } = {}) {
  checkManifest(manifest, expectedAccount, now);
  const folder = await mkdtemp(join(tmpdir(), 'distribution-'));
  const path = join(folder, 'original.mp4');
  try {
    const response = await fetchVideo(manifest.videoUrl, { redirect: 'error', signal: AbortSignal.timeout(60_000) });
    if (response.status !== 200 || !response.body ||
      response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'video/mp4') {
      await response.body?.cancel();
      throw new Error(`MP4 no disponible (HTTP ${response.status})`);
    }
    let bytes = 0;
    const limit = new Transform({
      transform(chunk, _encoding, done) {
        bytes += chunk.length;
        done(bytes > manifest.size ? new Error('MP4 excede tamaño esperado') : null, chunk);
      },
    });
    await pipeline(Readable.fromWeb(response.body), limit, createWriteStream(path, { flags: 'wx', mode: 0o600 }));
    assert((await stat(path)).size === manifest.size, 'MP4 incompleto');
    assert(await sha256Mp4(path) === manifest.mediaSha256, 'SHA-256 no coincide');
    const { stdout } = await probe('ffprobe', ['-v', 'error', '-show_entries',
      'format=duration:stream=codec_type', '-of', 'json', path], { timeout: 15_000 });
    const info = JSON.parse(stdout);
    assert(['audio', 'video'].every(type => info.streams?.some(stream => stream.codec_type === type)) &&
      Math.abs(Number(info.format?.duration) - manifest.duration) <= 0.05, 'Contenido o duración MP4 inválidos');
    return await useVideo(path);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}

export function openLedger(path) {
  assert(path && path !== ':memory:', 'Se requiere una ruta persistente');
  const db = new DatabaseSync(resolve(path), { timeout: 5000 });
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = FULL;
    CREATE TABLE IF NOT EXISTS distribution (
      brand TEXT NOT NULL, platform TEXT NOT NULL, edition TEXT NOT NULL, hash TEXT NOT NULL,
      manifest TEXT NOT NULL, state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
      post_id TEXT, publication_id TEXT, revision TEXT, evidence TEXT NOT NULL DEFAULT '{}',
      PRIMARY KEY (brand, platform, edition, hash),
      UNIQUE (brand, platform, edition),
      UNIQUE (brand, platform, hash),
      UNIQUE (platform, publication_id)
    );
  `);
  return db;
}

export function reserve(db, manifest, accountId, now = new Date()) {
  checkManifest(manifest, accountId, now);
  assert(!historicalOrbiuno.has(manifest.editionId), 'Edición histórica ya entregada a TikTok');
  db.prepare(`INSERT INTO distribution (brand, platform, edition, hash, manifest, state)
    VALUES (?, 'tiktok', ?, ?, ?, 'pending')`)
    .run(manifest.brand, manifest.editionId, manifest.mediaSha256, JSON.stringify(manifest));
  return get(db, manifest.editionId);
}

export function get(db, edition) {
  return db.prepare("SELECT * FROM distribution WHERE platform = 'tiktok' AND edition = ?").get(edition);
}

export function advance(db, edition, version, state, evidence) {
  const row = get(db, edition);
  assert(row?.version === version && Object.hasOwn(transitions, row.state) &&
    transitions[row.state].includes(state), 'La transición ya ocurrió o es inválida');
  assert(evidence && typeof evidence.reference === 'string' && evidence.reference.trim(), 'Falta evidencia');
  const post = row.post_id ?? evidence.postId ?? null;
  const publication = row.publication_id ?? evidence.publicationId ?? null;
  const revision = row.revision ?? evidence.revision ?? null;
  assert([['postId', post], ['publicationId', publication], ['revision', revision]].every(([key, value]) =>
    value === null || (typeof value === 'string' && value.trim() &&
      (evidence[key] === undefined || evidence[key] === value))), 'Identificadores inconsistentes');
  if (['draft', 'approved', 'submitted', 'processing', 'completed', 'failed'].includes(state)) {
    assert(post && publication && revision, 'Faltan identificadores de la revisión vidIQ');
  }
  if (state === 'approved') assert(evidence.ownerApproved === true, 'Falta aprobación de la revisión');
  if (state === 'submitted') {
    assert(JSON.parse(row.manifest).accountId === evidence.accountId &&
      evidence.canPublish === true && evidence.historyChecked === true, 'Cuenta o historial sin verificar');
  }
  if (state === 'completed' && evidence.url !== undefined) {
    assert(/^https:\/\/www\.tiktok\.com\/@[\w.]+\/video\/\d+$/.test(evidence.url), 'URL TikTok inválida');
  }
  const result = db.prepare(`UPDATE distribution SET state=?, version=version+1,
    post_id=?, publication_id=?, revision=?, evidence=json_patch(evidence, ?)
    WHERE edition=? AND platform='tiktok' AND version=?`)
    .run(state, post, publication, revision,
      JSON.stringify({ [state]: { ...evidence, recordedAt: new Date().toISOString() } }), edition, version);
  assert(result.changes === 1, 'Otra ejecución tomó la reserva');
  return get(db, edition);
}

export function promotionEligibility(history, now = new Date()) {
  assert(history?.complete === true && Number.isFinite(now.getTime()), 'Historial de promociones incompleto');
  const campaigns = history.promotions.map(promotion => {
    const time = Date.parse(promotion.publishedAt);
    assert(promotion.verified === true && promotion.id && Number.isFinite(time) && time <= now.getTime(),
      'Promoción pendiente de conciliación');
    return time;
  });
  if (!campaigns.length) return { eligible: true, nextEligibleAt: null };
  const next = Math.max(...campaigns) + 7 * 86_400_000;
  return { eligible: now.getTime() >= next, nextEligibleAt: new Date(next).toISOString() };
}

export function rankPosts(posts, now = new Date()) {
  const weights = { reach: 0.22, views: 0.1, shares: 0.30, saves: 0.25, interactions: 0.13 };
  return posts.flatMap(post => {
    const age = (now.getTime() - Date.parse(post.publishedAt)) / 86_400_000;
    if (post.alreadyPromoted || post.relevant !== true || !Number.isFinite(age) || age < 0 || age > 14) return [];
    let score = 0;
    for (const [field, weight] of Object.entries(weights)) {
      const metric = post[field];
      if (Number.isFinite(metric) && metric >= 0) score += weight * Math.log1p(metric);
    }
    return [{ ...post, score: score * 2 ** (-age / 7) }];
  }).sort((a, b) => b.score - a.score || b.publishedAt.localeCompare(a.publishedAt));
}

async function main([command, dbPath, argument, extra, state, evidencePath]) {
  if (command === 'promotion') return promotionEligibility(JSON.parse(await readFile(dbPath, 'utf8')));
  if (command === 'rank') return rankPosts(JSON.parse(await readFile(dbPath, 'utf8')));
  const db = openLedger(dbPath);
  try {
    if (command === 'validate') {
      const manifest = JSON.parse(await readFile(argument, 'utf8'));
      await withVerifiedVideo(manifest, extra, () => {});
      const existing = get(db, manifest.editionId);
      const row = existing ?? reserve(db, manifest, extra);
      assert(row.manifest === JSON.stringify(manifest) && row.state === 'pending',
        'Edición ya registrada o manifiesto distinto');
      return advance(db, manifest.editionId, row.version, 'validated', { reference: manifest.mediaSha256 });
    }
    if (command === 'get') return get(db, argument) ?? null;
    if (command === 'advance') {
      assert(state !== 'validated', 'La validación requiere descarga e inspección');
      return advance(db, argument, Number(extra), state, JSON.parse(await readFile(evidencePath, 'utf8')));
    }
    throw new Error('Comando esperado: validate, get, advance, promotion o rank');
  } finally {
    db.close();
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  main(process.argv.slice(2)).then(result => console.log(JSON.stringify(result, null, 2))).catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
