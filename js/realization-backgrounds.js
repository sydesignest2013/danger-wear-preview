(()=>{
 const root=new URL('../',document.currentScript.src);
 fetch(new URL('assets/realization-backgrounds/settings.json',root),{cache:'no-cache'})
 .then(r=>{if(!r.ok)throw Error('background settings');return r.json()})
 .then(settings=>{
  for(const theme of ['light','dark']){
   const value=settings[theme];if(typeof value!=='string'||!value.trim())continue;
   const url=new URL(value,root);if(url.origin!==root.origin)return;
   document.documentElement.style.setProperty('--dw-realization-'+theme,`url("${url.href.replaceAll('"','%22')}")`);
  }
 }).catch(()=>{/* Neutral backgrounds stay available without configuration. */});
})();
