(() => {
const toggle=document.querySelector('#sidebarToggle'),sidebarKey='dw-panel-sidebar-collapsed';
function setSidebar(collapsed){document.body.classList.toggle('sidebar-collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));toggle.setAttribute('aria-label',collapsed?'Rozwiń menu':'Zwiń menu');toggle.textContent=collapsed?'›':'‹';localStorage.setItem(sidebarKey,collapsed?'1':'0');}
setSidebar(localStorage.getItem(sidebarKey)==='1');toggle.addEventListener('click',()=>setSidebar(!document.body.classList.contains('sidebar-collapsed')));
let frame;
function openSocial(event){event.preventDefault();if(typeof canLeave==='function'&&!canLeave())return;
 if(!frame){frame=document.createElement('iframe');frame.title='DW Social Media';frame.src='http://127.0.0.1:8786/?embedded=1';frame.style.cssText='position:fixed;inset:0;width:100%;height:100dvh;border:0;z-index:500;background:#090b0c';document.body.append(frame);}frame.hidden=false;history.replaceState(null,'','#social');}
document.querySelectorAll('[data-open-social]').forEach(b=>b.addEventListener('click',openSocial));
window.addEventListener('message',e=>{if(!frame||e.source!==frame.contentWindow||e.origin!=='http://127.0.0.1:8786')return;if(e.data==='dw-panel'){frame.hidden=true;history.replaceState(null,'',location.pathname);}if(e.data==='dw-logout'){frame.hidden=true;document.querySelector('#logout').click();}if(e.data==='dw-password'){frame.hidden=true;document.querySelector('#changePassword').click();}});
if(location.hash==='#social')openSocial({preventDefault(){}});
})();
