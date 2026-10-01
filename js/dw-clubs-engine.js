// One engine for the public galleries. Club names never become photo captions.
export function engine(data, random = Math.random) {
  const edges = new Set((data.rivalries || []).flatMap(([a,b]) => [a+'|'+b,b+'|'+a]));
  const owner = p => Object.prototype.hasOwnProperty.call(data.photos || {},p.src) ? data.photos[p.src] : (p.club_id || null);
  const rival = (a,b) => !!a && !!b && edges.has(a+'|'+b);
  const weight = id => Math.max(1,Math.min(1.2,Number(data.clubs?.[id]?.weight) || 1));
  const unique = photos => [...new Map((photos || []).filter(p=>p && typeof p.src==='string').map(p=>[p.src,p])).values()];
  function pick(photos) {
    const groups = new Map();
    for (const p of photos) { const id=owner(p); if(!groups.has(id))groups.set(id,[]);groups.get(id).push(p); }
    const ids=[...groups.keys()]; let cursor=random()*ids.reduce((s,id)=>s+weight(id),0),id=ids.at(-1);
    for (const key of ids) {cursor-=weight(key);if(cursor<0){id=key;break;}}
    const group=groups.get(id);return group?.[Math.min(group.length-1,Math.floor(random()*group.length))];
  }
  function lifestyle(photos,limit=5) {
    let pool=unique(photos),out=[];
    while(pool.length && out.length<limit){const p=pick(pool);out.push(p);pool=pool.filter(q=>q.src!==p.src&&!rival(owner(q),owner(p)));}
    return out;
  }
  function realizacje(photos,limit=18) {
    let pool=unique(photos),out=[];
    while(pool.length && out.length<limit){
      const allowed=pool.filter(p=>out.every((q,i)=>!rival(owner(q),owner(p)) || out.slice(i+1).some(m=>!rival(owner(m),owner(q))&&!rival(owner(m),owner(p)))));
      if(!allowed.length)break;
      const p=pick(allowed);out.push(p);pool=pool.filter(q=>q.src!==p.src);
    }
    return out;
  }
  function production(methods,previous={}) {
    const slots=Object.keys(methods).sort((a,b)=>methods[a].length-methods[b].length),ordered={};
    for(const key of slots){
      let pool=unique(methods[key]),order=[];
      // Club first; previous photo is moved within its club, preserving the club weight.
      while(pool.length){const p=pick(pool),id=owner(p),group=pool.filter(q=>owner(q)===id&&q!==p);for(let i=group.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[group[i],group[j]]=[group[j],group[i]];}group.unshift(p);group.sort((a,b)=>(a.src===previous[key])-(b.src===previous[key]));order.push(...group);pool=pool.filter(q=>owner(q)!==id);}
      ordered[key]=order;
    }
    let best={},bestCount=-1,steps=0;
    function search(i,chosen,distinct,skip){
      if(++steps>30000)return false;
      const values=Object.values(chosen),count=values.length;
      if(count>bestCount){best={...chosen};bestCount=count;}
      if(i===slots.length)return count===slots.length;
      const key=slots[i];
      for(const p of ordered[key]){
        if(values.some(q=>q.src===p.src||rival(owner(p),owner(q))||(distinct&&owner(p)&&owner(p)===owner(q))))continue;
        chosen[key]=p;if(search(i+1,chosen,distinct,skip))return true;delete chosen[key];
      }
      return skip?search(i+1,chosen,distinct,skip):false;
    }
    if(!search(0,{},true,false)){steps=0;if(!search(0,{},false,false)){steps=0;search(0,{},false,true);}}
    return best;
  }
  return {owner,rival,pick,lifestyle,realizacje,production};
}
export async function load(base) {
  const response=await fetch(new URL('dw-clubs-data.json',base),{cache:'no-store'});
  if(!response.ok)throw new Error('Club database unavailable');
  const data=await response.json();
  if(data.version!==1||!Array.isArray(data.rivalries)||!data.clubs||!data.photos)throw new Error('Invalid club database');
  return {data,...engine(data)};
}
