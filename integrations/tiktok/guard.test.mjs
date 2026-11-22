import test from 'node:test';
import assert from 'node:assert/strict';
import {validateEdition,ensureUnique,readLedger} from './guard.mjs';
const e={brand:'ORBIUNO',editionId:'ORBIUNO_20261122_0800',approved:true,rightsConfirmed:true,approvedAt:'2026-11-22T12:00:00Z',mediaSha256:'a'.repeat(64),accountId:'verified'};
test('edición aprobada',()=>assert.equal(validateEdition(e,new Date('2026-11-22T13:00:00Z')),e));
test('caducidad',()=>assert.throws(()=>validateEdition(e,new Date('2026-11-25T13:00:00Z'))));
test('duplicados',()=>assert.throws(()=>ensureUnique(e,[e])));
test('bitácora nueva',async()=>assert.deepEqual(await readLedger('/tmp/ledger-tiktok-nonexistent-20261122.json'),[]));
