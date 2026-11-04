/**
 * Cloudflare Pages Function: eventos de audio sin cookies ni datos personales.
 * Para métricas persistentes configurar binding Analytics Engine:
 * ANALYTICS_ENGINE -> dataset orbiuno_audio (en Cloudflare Pages > Settings).
 *
 * Sin binding devuelve recorded:false; jamás finge haber almacenado un evento.
 * No guardar dirección IP, User-Agent ni identificadores individuales.
 */
const VALID_EVENTS=new Set(["audio_play","audio_finished","audio_paused","audio_resumed"]);
const VALID_SPEED=new Set([1,1.25,1.5,2]);
const VALID_MODE=new Set(["complete_orbiuno","complete_licensed","summary"]);
const VALID_TONE=new Set(["dulce","juvenil","natural"]);
const SAFE_ID=/^[a-z0-9_-]{1,120}$/i;
const SAFE_ATTR=/^[a-z0-9_-]{0,75}$/i;

export async function onRequestPost(context) {
  const {request,env}=context;
  const origin=request.headers.get("origin");
  if(origin && origin!==new URL(request.url).origin) {
    return Response.json({recorded:false,error:"origin_not_allowed"},{status:403});
  }
  if(request.headers.get("content-type")?.split(";")[0] !== "application/json") {
    return Response.json({recorded:false,error:"json_required"},{status:415});
  }
  const length=Number(request.headers.get("content-length")||0);
  if(length>3000) return Response.json({recorded:false,error:"payload_too_large"},{status:413});
  let payload;
  try{
    const body=await request.text();
    if(body.length>3000) throw Error("too large");
    payload=JSON.parse(body);
  }catch(error){return Response.json({recorded:false,error:"invalid_json"},{status:400});}
  if(!payload || !VALID_EVENTS.has(payload.event) ||
     !SAFE_ID.test(payload.articleId||"") ||
     !VALID_SPEED.has(payload.speed) ||
     !VALID_MODE.has(payload.mode) ||
     !VALID_TONE.has(payload.tone) ||
     (payload.source && !SAFE_ATTR.test(payload.source)) ||
     (payload.medium && !SAFE_ATTR.test(payload.medium)) ||
     (payload.campaign && !SAFE_ATTR.test(payload.campaign))) {
    return Response.json({recorded:false,error:"invalid_event"},{status:400});
  }

  if(!env.ANALYTICS_ENGINE || typeof env.ANALYTICS_ENGINE.writeDataPoint!=="function") {
    return Response.json({recorded:false,reason:"analytics_binding_not_configured"},
                         {headers:{"Cache-Control":"no-store"}});
  }
  try{
    env.ANALYTICS_ENGINE.writeDataPoint({
      indexes:["orbiuno-audio"],
      blobs:[payload.event,payload.articleId,payload.mode,payload.tone,
             payload.source||"direct",payload.medium||"none",payload.campaign||"none"],
      doubles:[1,payload.speed],
    });
    return Response.json({recorded:true},{headers:{"Cache-Control":"no-store"}});
  }catch(error){
    return Response.json({recorded:false,reason:"analytics_engine_unavailable"},
                         {status:503,headers:{"Cache-Control":"no-store"}});
  }
}
export function onRequestGet() {
  return Response.json({recorded:false,reason:"post_event_required"},{status:405});
}
