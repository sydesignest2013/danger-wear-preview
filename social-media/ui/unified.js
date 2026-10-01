(() => {const embedded=window.parent!==window;
const toggle=document.querySelector('#sidebarToggle'),sidebarKey='dw-social-sidebar-collapsed';
function setSidebar(collapsed){document.body.classList.toggle('sidebar-collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));toggle.setAttribute('aria-label',collapsed?'Rozwiń menu':'Zwiń menu');toggle.textContent=collapsed?'›':'‹';localStorage.setItem(sidebarKey,collapsed?'1':'0');}
setSidebar(localStorage.getItem(sidebarKey)==='1');toggle.addEventListener('click',()=>setSidebar(!document.body.classList.contains('sidebar-collapsed')));
document.querySelectorAll('a[href="http://127.0.0.1:8765/admin/"]').forEach(a=>a.addEventListener('click',e=>{if(!embedded)return;e.preventDefault();parent.postMessage('dw-panel','http://127.0.0.1:8765');}));
const box=document.createElement('div');box.className='dw-account';[['Zmień hasło','dw-password'],['Wyloguj','dw-logout']].forEach(([label,msg])=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>{if(embedded)return parent.postMessage(msg,'http://127.0.0.1:8765');window.location.href='http://127.0.0.1:8765/admin/';};box.append(b)});document.querySelector('.sidebar-bottom').prepend(box);
})();
