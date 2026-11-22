import {createHash} from 'node:crypto';
import {readFile,writeFile,rename,open,unlink} from 'node:fs/promises';
import {resolve} from 'node:path';
export function validateEdition(e,now=new Date()){
 if(!e||!['ORBIUNO','MYCAR'].includes(e.brand))throw Error('Marca inválida');
 if(!/^[\w-]{8,100}$/.test(e.editionId||''))throw Error('Edición inválida');
 if(e.approved!==true||e.rightsConfirmed!==true)throw Error('Faltan aprobaciones');
 if(!/^[a-f0-9]{64}$/.test(e.mediaSha256||'')||!e.accountId)throw Error('Medio o cuenta no verificados');
 const age=now.getTime()-Date.parse(e.approvedAt);
 if(!Number.isFinite(age)||age<0||age>36*3600000)throw Error('Edición no vigente');
 return e;
}
export function ensureUnique(e,ledger){
 if(!Array.isArray(ledger))throw Error('Bitácora inválida');
 if(ledger.some(x=>x.brand===e.brand&&(x.editionId===e.editionId||x.mediaSha256===e.mediaSha256)))throw Error('Duplicado');
}
export async function sha256Mp4(path){
 const bytes=await readFile(resolve(path));
 if(bytes.length<1024||bytes.toString('ascii',4,8)!=='ftyp')throw Error('MP4 inválido');
 return createHash('sha256').update(bytes).digest('hex');
}
export async function readLedger(path){
 try{const data=JSON.parse(await readFile(resolve(path),'utf8'));if(!Array.isArray(data))throw Error('Bitácora inválida');return data;}
 catch(err){if(err.code==='ENOENT')return [];throw err;}
}
export async function recordCompleted(path,e,proof){
 validateEdition(e);
 if(!proof||proof.status!=='completed'||!proof.publicationId||
 !/^https:\/\/www\.tiktok\.com\/@[^/]+\/video\/\d+$/.test(proof.url||''))throw Error('Sin prueba TikTok');
 const target=resolve(path), lock=target+'.lock',handle=await open(lock,'wx');
 try{const rows=await readLedger(target);ensureUnique(e,rows);
 rows.push({...e,publicationId:proof.publicationId,url:proof.url,verifiedAt:new Date().toISOString()});
 const tmp=target+'.'+process.pid+'.tmp';await writeFile(tmp,JSON.stringify(rows,null,2)+'\n',{flag:'wx'});await rename(tmp,target);
 }finally{await handle.close();await unlink(lock);}
}
