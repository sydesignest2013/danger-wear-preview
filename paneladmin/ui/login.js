'use strict';
(()=>{
 const by=id=>document.getElementById(id);let setup=false;
 const error=message=>{by('loginError').textContent=message;by('loginError').hidden=false};
 async function load(){
  try{const response=await fetch(window.DW_BASE+'/api/auth');if(!response.ok)throw Error('Nie można odczytać stanu logowania.');const state=await response.json();if(state.authenticated){location.replace(window.DW_BASE+'/');return}setup=!state.configured;by('loginTitle').textContent=setup?'Ustaw hasło':'Zaloguj się';by('loginDescription').textContent=setup?'Pierwsze uruchomienie zabezpieczonego panelu. Ustaw własne hasło — co najmniej 12 znaków.':'Wpisz swoje hasło, aby zarządzać produktami Danger Wear.';by('confirmationLabel').hidden=!setup;by('confirmation').required=setup;by('password').autocomplete=setup?'new-password':'current-password';by('password').minLength=setup?12:1;by('loginSubmit').textContent=setup?'Ustaw hasło i otwórz panel →':'Zaloguj się →';by('loginForm').hidden=false;by('password').focus()}
  catch(e){by('loginDescription').textContent='Program nie odpowiada. Sprawdź, czy jest uruchomiony, i odśwież stronę.';error(e.message)}
 }
 by('showPassword').onchange=e=>{by('password').type=by('confirmation').type=e.target.checked?'text':'password'};
 by('loginForm').onsubmit=async e=>{
  e.preventDefault();by('loginError').hidden=true;
  if(setup&&by('password').value!==by('confirmation').value){error('Wpisane hasła nie są takie same.');return}
  by('loginSubmit').disabled=true;
  try{const response=await fetch(window.DW_BASE+'/api/'+(setup?'setup':'login'),{method:'POST',headers:{'Content-Type':'application/json','X-DW-Token':window.DW_TOKEN},body:JSON.stringify({password:by('password').value,confirmation:by('confirmation').value})});const result=await response.json();if(!response.ok)throw Error(result.error||'Logowanie nie powiodło się.');by('password').value=by('confirmation').value='';location.replace(window.DW_BASE+'/')}
  catch(e){error(e.message);by('password').select();by('loginSubmit').disabled=false}
 };
 load();
})();
