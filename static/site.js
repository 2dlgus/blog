(function(){
  var root=document.documentElement;
  var tb=document.getElementById('theme');
  if(tb)tb.addEventListener('click',function(){
    var dark=root.dataset.theme==='dark'||(!root.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);
    var next=dark?'light':'dark';root.dataset.theme=next;
    try{localStorage.setItem('theme',next)}catch(e){}
    var f=document.querySelector('iframe.giscus-frame');
    if(f)f.contentWindow.postMessage({giscus:{setConfig:{theme:next}}},'https://giscus.app');
  });
  var mb=document.getElementById('menu'),dr=document.getElementById('drawer');
  if(mb&&dr)mb.addEventListener('click',function(){var on=dr.classList.toggle('on');mb.setAttribute('aria-expanded',on)});
  var segOn=document.querySelector('.seg a.on');if(segOn&&segOn.parentNode.scrollWidth>segOn.parentNode.clientWidth)segOn.parentNode.scrollLeft=segOn.getBoundingClientRect().left-segOn.parentNode.getBoundingClientRect().left-20;
  // pagination
  document.querySelectorAll('ul.list[data-page]').forEach(function(ul){
    var per=+ul.dataset.page,items=[].slice.call(ul.children),pages=Math.ceil(items.length/per),pager=ul.nextElementSibling;
    if(pages<2||!pager)return;
    function show(n){items.forEach(function(li,i){li.hidden=Math.floor(i/per)!==n-1});
      pager.innerHTML='';
      var go=function(k){return function(){show(k);history.replaceState(null,'','#p'+k);ul.closest('.card').scrollIntoView()}};
      var add=function(t,k,on,lab){var b=document.createElement('button');b.type='button';b.textContent=t;if(lab)b.setAttribute('aria-label',lab);if(on)b.className='on';if(k<1||k>pages||k===n&&!on)b.disabled=true;else if(!on)b.onclick=go(k);pager.appendChild(b)};
      var s=Math.max(1,Math.min(n-2,pages-4)),e=Math.min(pages,s+4);
      add('‹',n-1,false,'이전');for(var i=s;i<=e;i++)add(i,i,i===n);add('›',n+1,false,'다음')}
    var m=location.hash.match(/^#p(\d+)$/);show(m?Math.min(+m[1],pages):1);
  });
  // search
  var q=document.getElementById('q'),res=document.getElementById('results');
  if(q&&res){
    var data=null,esc=function(s){return String(s).replace(/[&<>"]/g,function(m){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]})};
    fetch('/search.json').then(function(r){return r.json()}).then(function(d){data=d;var u=new URLSearchParams(location.search).get('q');if(u){q.value=u;run()}});
    function run(){
      if(!data)return;var w=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      if(!w.length){res.innerHTML='';return}
      var hit=data.filter(function(p){var s=(p.t+' '+p.e+' '+p.g.join(' ')+' '+p.c).toLowerCase();return w.every(function(x){return s.indexOf(x)>-1})});
      res.innerHTML=hit.length?hit.slice(0,50).map(function(p){return '<li><a href="/'+p.i+'" style="grid-template-columns:1fr"><div><p class="lt">'+esc(p.t)+'</p><p class="le">'+esc(p.e)+'</p><div class="lm"><span class="cat">'+esc(p.c.replace('/',' · '))+'</span><span class="dot"></span><span>'+p.d+'</span></div></div></a></li>'}).join(''):'<li class="empty">결과 없음</li>';
    }
    q.addEventListener('input',run);q.focus();
  }
})();
