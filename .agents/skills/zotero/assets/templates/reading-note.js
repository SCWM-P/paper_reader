(() => {
  const root = document.documentElement;
  const search = document.getElementById('note-search');
  const darkButton = document.getElementById('theme-toggle');
  const focusButton = document.getElementById('focus-toggle');
  const status = document.getElementById('search-status');
  const sections = Array.from(document.querySelectorAll('#reading-content > section'));
  document.querySelectorAll('.qa-list').forEach(list => {
    const tools=list.previousElementSibling, cards=[...list.querySelectorAll('.qa-card')];
    tools.querySelector('.qa-expand').addEventListener('click',()=>cards.forEach(c=>c.open=true));
    tools.querySelector('.qa-collapse').addEventListener('click',()=>cards.forEach(c=>c.open=false));
    tools.querySelector('.qa-search').addEventListener('input',e=>{
      const query=e.target.value.trim().toLocaleLowerCase();let count=0;
      cards.forEach(c=>{c.hidden=Boolean(query && !c.textContent.toLocaleLowerCase().includes(query));if(!c.hidden)count++;});
      tools.querySelector('.qa-count').textContent=query?`${count} 条讨论`:'';
    });
  });
  document.querySelectorAll('.copy-code').forEach(button=>button.addEventListener('click',async()=>{
    const panel=button.closest('.code-panel'), code=panel.querySelector('code'), status=panel.querySelector('.copy-status');
    try{await navigator.clipboard.writeText(code.textContent);status.textContent='已复制';}
    catch(_){const selection=window.getSelection(),range=document.createRange();range.selectNodeContents(code);selection.removeAllRanges();selection.addRange(range);status.textContent=document.execCommand('copy')?'已复制':'代码已选中，可手动复制';}
  }));
  let printState=[];
  window.addEventListener('beforeprint',()=>{printState=[...document.querySelectorAll('.qa-card')].map(c=>[c,c.open]);printState.forEach(([c])=>c.open=true);});
  window.addEventListener('afterprint',()=>{printState.forEach(([c,open])=>c.open=open);printState=[];});
  if (!search || !darkButton || !focusButton || !status) return;
  function setDark(value) {
    root.dataset.dark = String(value);
    darkButton.setAttribute('aria-pressed', String(value));
    darkButton.textContent = value ? '浅色模式' : '深色模式';
  }
  let saved = null;
  try { saved = localStorage.getItem('zotero-reading-dark'); } catch (_) {}
  setDark(saved === null ? window.matchMedia('(prefers-color-scheme: dark)').matches : saved === 'true');
  darkButton.addEventListener('click', () => {
    const next = root.dataset.dark !== 'true';
    setDark(next);
    try { localStorage.setItem('zotero-reading-dark', String(next)); } catch (_) {}
  });
  focusButton.addEventListener('click', () => {
    const value = document.body.classList.toggle('focus');
    focusButton.setAttribute('aria-pressed', String(value));
    focusButton.textContent = value ? '显示目录' : '专注阅读';
  });
  document.getElementById('print-note')?.addEventListener('click', () => window.print());
  search.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    let count = 0;
    sections.forEach(section => {
      const match = Boolean(query && section.textContent.toLocaleLowerCase().includes(query));
      section.classList.toggle('search-hit', match);
      if (match) count++;
    });
    status.textContent = query ? `${count} 个章节包含该词；正文始终完整保留。` : '';
  });
  function updateProgress() {
    const total = root.scrollHeight - window.innerHeight;
    const fill = document.getElementById('progress-fill');
    if (fill) fill.style.width = `${total > 0 ? Math.min(100, Math.max(0, window.scrollY / total * 100)) : 100}%`;
  }
  window.addEventListener('scroll', updateProgress, {passive: true});
  window.addEventListener('resize', updateProgress);
  updateProgress();
})();
