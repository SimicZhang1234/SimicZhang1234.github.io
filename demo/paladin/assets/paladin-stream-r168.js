(()=>{'use strict';
const base=new URL('r168-stream/',document.currentScript.src);
const videos=[...document.querySelectorAll('video[data-paladin-stream]')];
for(const video of videos){let started=false;
const status=document.createElement('p');status.style.cssText='font-size:14px;color:inherit;opacity:.8';status.textContent='1080p · 完整影片，点击播放';video.after(status);
async function begin(){if(started)return;started=true;
try{const cfg=await fetch(new URL('stream.json',base)).then(r=>{if(!r.ok)throw Error('影片信息加载失败');return r.json()});
const MS=window.MediaSource||window.ManagedMediaSource;
if(!MS||!cfg.tracks.every(t=>MS.isTypeSupported(t.mime)))throw Error('此浏览器暂不支持连续影片，请使用下方章节短片或上一版完整影片');
video.disableRemotePlayback=true;const ms=new MS();video.src=URL.createObjectURL(ms);
await new Promise((resolve,reject)=>{ms.addEventListener('sourceopen',resolve,{once:true});ms.addEventListener('error',reject,{once:true})});ms.duration=cfg.seconds;
const buffers=cfg.tracks.map(t=>ms.addSourceBuffer(t.mime));
const append=(sb,data)=>new Promise((resolve,reject)=>{sb.addEventListener('updateend',resolve,{once:true});sb.addEventListener('error',reject,{once:true});try{sb.appendBuffer(data)}catch(e){reject(e)}});
await Promise.all(cfg.tracks.map(async(t,i)=>{for(const file of [t.init,...t.segments]){const r=await fetch(new URL(file,base));if(!r.ok)throw Error('影片分段加载失败，请刷新重试');await append(buffers[i],await r.arrayBuffer());if(file===t.init)video.play().catch(()=>{});}}));
if(ms.readyState==='open')ms.endOfStream();status.textContent='1080p · 完整影片已加载 · 可拖动时间轴';
}catch(e){status.textContent=e.message||'影片加载失败，请刷新重试';}}
video.addEventListener('play',begin,{once:true});video.addEventListener('pointerdown',begin,{once:true});video.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' ')begin()});video.tabIndex=0;
}})();