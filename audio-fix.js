/* ORBIUNO: reproductor local para iPhone, Safari y navegadores móviles.
   Los MP3 son propios y se reproducen en la misma página. */
(()=>{
'use strict';
const defaultRate=1.25;
const rates=[1,1.25,1.5,2];
let rate=defaultRate, manifest=null, currentId=null, nativeToken=0;
let queue=[],queueIndex=-1,paused=false,usingNative=false;
const player=new Audio();
player.preload='none';
player.playsInline=true;
player.preservesPitch=true;
const entries=()=>{try{return JSON.parse(document.getElementById('initial-news')?.textContent||'{}').news||[]}catch{return []}};
let news=entries();
const byId=id=>news.find(n=>n.id===id);
const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
const textOf=n=>(n?.originalArticleReviewed===true && n?.originalArticleByline==='Redacción ORBIUNO' && n?.originalArticleTextEs?.trim()) || n?.audioFullTextEs?.trim() || n?.executiveSummary || n?.summary || '';
const narration=n=>n?.title+'. Fuente: '+(n?.sources?.[0]?.name||'ORBIUNO')+'. '+textOf(n);
const urlFor=n=>{
 const a=manifest?.items?.[n?.id];
 if(!a?.url || !a?.text || clean(a.text)!==clean(narration(n)))return '';
 if(!/^\.\/media\/web-voice\/[a-z0-9-]+\.mp3$/.test(a.url))return '';
 return a.url;
};
fetch('./media/web-voice/manifest.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('manifest unavailable');return r.json()})
 .then(m=>{manifest=m})
 .catch(()=>{manifest=null});
const buttons=id=>Array.from(document.querySelectorAll('[data-tts-action="toggle"]')).filter(b=>b.dataset.ttsId===id);
const resetButtons=()=>{
 document.querySelectorAll('[data-tts-action="toggle"]').forEach(b=>{
   b.setAttribute('aria-pressed','false');
   b.textContent='▶ '+(b.getAttribute('aria-label')||'Escuchar noticia');
 });
 document.querySelectorAll('[data-tts-action="stop"]').forEach(b=>b.hidden=true);
 const all=document.getElementById('listen-edition');if(all){all.textContent='▶ Escuchar todas';all.setAttribute('aria-pressed','false')}
 const stop=document.getElementById('stop-edition');if(stop)stop.hidden=true;
};
const markPlaying=(id,isPause=false)=>{
 resetButtons();
 buttons(id).forEach(b=>{b.textContent=isPause?'▶ Reanudar':'❚❚ Pausar';b.setAttribute('aria-pressed',isPause?'false':'true')});
 document.querySelectorAll('[data-tts-action="stop"]').forEach(b=>{if(b.dataset.ttsId===id)b.hidden=false});
 if(queue.length){const all=document.getElementById('listen-edition');if(all){all.textContent='❚❚ Pausar todas';all.setAttribute('aria-pressed','true')}const stop=document.getElementById('stop-edition');if(stop)stop.hidden=false}
};
const stopAudio=(clearQueue=true)=>{
 nativeToken++;
 try{player.pause();player.removeAttribute('src');player.load()}catch{}
 try{window.speechSynthesis?.cancel()}catch{}
 paused=false;usingNative=false;currentId=null;
 if(clearQueue){queue=[];queueIndex=-1}
 resetButtons();
};
const chunksOf=text=>{
 const paragraphs=String(text).split(/(?<=[.!?;:])\s+/);
 const chunks=[];let chunk='';
 for(const sentence of paragraphs){
   if((chunk+' '+sentence).length>170 && chunk){chunks.push(chunk);chunk=''}
   if(sentence.length>170){for(let i=0;i<sentence.length;i+=160){if(chunk){chunks.push(chunk);chunk=''}chunks.push(sentence.slice(i,i+160))}}
   else chunk+=(chunk?' ':'')+sentence;
 }
 if(chunk)chunks.push(chunk);
 return chunks;
};
const nextInQueue=()=>{
 if(queue.length && ++queueIndex<queue.length)play(queue[queueIndex],true);
 else stopAudio();
};
const nativeSpeak=(id,body)=>{
 const synth=window.speechSynthesis;
 if(!synth || !window.SpeechSynthesisUtterance){showError(id,'Tu navegador no permitió reproducir el audio');return}
 const chunks=chunksOf(body);
 if(!chunks.length){showError(id,'Esta noticia todavía no tiene audio');return}
 usingNative=true;const token=++nativeToken;
 const voices=synth.getVoices();
 const voice=voices.find(v=>v.lang?.toLowerCase()==='es-co')||voices.find(v=>v.lang?.toLowerCase().startsWith('es-'))||null;
 let part=0;
 const speakPart=()=>{
   if(token!==nativeToken)return;
   if(part>=chunks.length){nextInQueue();return}
   const utterance=new SpeechSynthesisUtterance(chunks[part++]);
   utterance.lang='es-CO';if(voice)utterance.voice=voice;
   utterance.rate=rate;utterance.pitch=1;
   utterance.onend=()=>{if(token===nativeToken)speakPart()};
   utterance.onerror=()=>{if(token===nativeToken)showError(id,'El dispositivo interrumpió la lectura; toca para reintentar')};
   synth.speak(utterance);
 };
 synth.cancel();speakPart();markPlaying(id);
};
const showError=(id,message)=>{
 stopAudio();
 buttons(id).forEach(b=>{b.textContent='▶ Reintentar audio';b.title=message});
 console.warn('[ORBIUNO] '+message,id);
};
const play=(id,fromQueue=false)=>{
 const n=byId(id);if(!n)return;
 if(!fromQueue){queue=[];queueIndex=-1}
 if(currentId===id && paused && !usingNative){
   paused=false;player.play().then(()=>markPlaying(id)).catch(()=>nativeSpeak(id,narration(n)));return;
 }
 if(currentId===id && !paused){
   if(usingNative){try{window.speechSynthesis.pause()}catch{}}
   else player.pause();
   paused=true;markPlaying(id,true);return;
 }
 stopAudio(false);
 currentId=id;const txt=narration(n),src=urlFor(n);
 if(src){
   player.src=src;
   player.playbackRate=rate/(Number(manifest?.baseRate)||1.25);
   player.currentTime=0;
   // play() se inicia dentro del clic, sin await previo: requisito de Safari iOS.
   const result=player.play();
   if(result && typeof result.then==='function')result.then(()=>{if(currentId===id)markPlaying(id)})
     .catch(()=>{if(currentId===id)nativeSpeak(id,txt)});
   else markPlaying(id);
 } else nativeSpeak(id,txt);
};
player.addEventListener('ended',nextInQueue);
player.addEventListener('error',()=>{if(currentId && !usingNative){const id=currentId,n=byId(id);nativeSpeak(id,narration(n))}});
document.addEventListener('click',event=>{
 const btn=event.target.closest('button[data-tts-action],#listen-edition,#stop-edition');
 if(!btn)return;
 event.preventDefault();event.stopImmediatePropagation();
 if(btn.id==='stop-edition'){stopAudio();return}
 if(btn.id==='listen-edition'){
  if(queue.length && currentId){play(currentId,true);return}
  queue=Array.from(document.querySelectorAll('#ediciones-hoy .listen-btn[data-tts-id]')).map(b=>b.dataset.ttsId).filter((id,i,a)=>a.indexOf(id)===i);
  if(!queue.length)queue=news.filter(n=>n.date===document.getElementById('date')?.value && n.verification==='editorial_verified').map(n=>n.id);
  queueIndex=0;if(queue.length)play(queue[0],true);
  return;
 }
 const id=btn.dataset.ttsId;
 if(btn.dataset.ttsAction==='stop'){stopAudio();return}
 if(btn.dataset.ttsAction==='speed'){
   rate=rates[(rates.indexOf(rate)+1)%rates.length];
   document.querySelectorAll('[data-tts-action="speed"]').forEach(b=>{b.textContent=rate+'×';b.setAttribute('aria-label','Velocidad '+rate+'×')});
   if(!usingNative && player.src)player.playbackRate=rate/(Number(manifest?.baseRate)||1.25);
   return;
 }
 if(btn.dataset.ttsAction==='toggle'){
   if(currentId===id && paused && usingNative){paused=false;window.speechSynthesis.resume();markPlaying(id);return}
   play(id);
 }
},true);
document.addEventListener('visibilitychange',()=>{if(document.hidden && usingNative && !paused){try{window.speechSynthesis.pause()}catch{}}else if(!document.hidden && usingNative && !paused){try{window.speechSynthesis.resume()}catch{}}});
window.addEventListener('pagehide',()=>stopAudio());
document.querySelectorAll('[data-tts-action="speed"]').forEach(b=>{b.textContent='1.25×';b.setAttribute('aria-label','Velocidad 1.25×')});
})();