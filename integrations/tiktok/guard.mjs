import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { open, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const BRANDS = new Set(['ORBIUNO', 'MYCAR']);
const MAX_AGE_MS = 36 * 60 * 60 * 1000;
const SHA256 = /^[a-f0-9]{64}$/;
const VIDEO_URL = /^https:\/\/www\.tiktok\.com\/@[A-Za-z0-9._]+\/video\/\d+$/;

export function validateEdition(edition, now = new Date()) {
  if (!edition || typeof edition !== 'object' || !BRANDS.has(edition.brand)) throw new Error('Marca inválida');
  if (!/^[A-Za-z0-9_-]{8,100}$/.test(edition.editionId || '')) throw new Error('ID de edición inválido');
  if (edition.approved !== true || edition.rightsConfirmed !== true) throw new Error('Falta aprobación o derechos');
  if (!SHA256.test(edition.mediaSha256 || '')) throw new Error('SHA256 inválido');
  if (typeof edition.accountId !== 'string' || !edition.accountId.trim()) throw new Error('Cuenta sin verificar');
  const age = now.getTime() - Date.parse(edition.approvedAt);
  if (!Number.isFinite(age) || age < 0 || age > MAX_AGE_MS) throw new Error('Edición no vigente');
  return edition;
}

export function ensureUnique(edition, ledger) {
  if (!Array.isArray(ledger)) throw new Error('Bitácora inválida');
  // O(n) sobre entradas históricas; incluye registros pendientes para evitar reenvíos.
  if (ledger.some(row => row.brand === edition.brand &&
      (row.editionId === edition.editionId || row.mediaSha256 === edition.mediaSha256))) {
    throw new Error('Edición o MP4 ya registrado');
  }
}

export async function sha256Mp4(path) {
  const file = await open(resolve(path), 'r');
  try {
    const stat = await file.stat();
    if (!stat.isFile() || stat.size < 1024) throw new Error('MP4 demasiado pequeño');
    const header = Buffer.alloc(8);
    if ((await file.read(header, 0, 8, 0)).bytesRead !== 8 ||
        header.toString('ascii', 4, 8) !== 'ftyp') throw new Error('Cabecera MP4 inválida');
  } finally {
    await file.close();
  }
  const digest = createHash('sha256');
  for await (const chunk of createReadStream(resolve(path))) digest.update(chunk);
  return digest.digest('hex');
}

export async function readLedger(path) {
  try {
    const ledger = JSON.parse(await readFile(resolve(path), 'utf8'));
    if (!Array.isArray(ledger)) throw new Error('Bitácora corrupta');
    return ledger;
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
}

export async function recordCompleted(path, edition, proof, options = {}) {
  if (!proof || proof.status !== 'completed' ||
      typeof proof.publicationId !== 'string' || !proof.publicationId.trim() ||
      !VIDEO_URL.test(proof.url || '')) throw new Error('Falta prueba oficial completada');
  if (!edition || !BRANDS.has(edition.brand) || !edition.editionId ||
      !SHA256.test(edition.mediaSha256 || '') || !edition.accountId) throw new Error('Edición inválida');
  const target = resolve(path);
  const lockPath = target + '.lock';
  let lock;
  try {
    lock = await open(lockPath, 'wx');
  } catch (error) {
    if (error.code === 'EEXIST') throw new Error('Registro ocupado: no repetir publicación');
    throw error;
  }
  let temporary;
  try {
    const ledger = await readLedger(target);
    ensureUnique(edition, ledger);
    const row = { brand: edition.brand, editionId: edition.editionId,
      mediaSha256: edition.mediaSha256, accountId: edition.accountId,
      publicationId: proof.publicationId, url: proof.url,
      verifiedAt: (options.now || new Date()).toISOString() };
    temporary = target + '.' + process.pid + '.' + Date.now() + '.tmp';
    await writeFile(temporary, JSON.stringify([...ledger, row], null, 2) + '\n', { flag: 'wx' });
    await rename(temporary, target);
    return row;
  } finally {
    if (temporary) await unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; });
    await lock.close();
    await unlink(lockPath);
  }
}
