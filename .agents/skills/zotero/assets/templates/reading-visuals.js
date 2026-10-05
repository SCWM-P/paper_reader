/* Offline mathematical reading tools. Data and projections are illustrative. */
(() => {
  const article = document.getElementById('reading-content');
  if (article && window.renderMathInElement) {
    renderMathInElement(article, {delimiters: [
      {left:'$$',right:'$$',display:true},{left:'\\[',right:'\\]',display:true},
      {left:'\\(',right:'\\)',display:false},{left:'$',right:'$',display:false}
    ], throwOnError:false, trust:false});
  }
  document.querySelectorAll('.figure-zoom').forEach(button => {
    button.addEventListener('click', () => {
      const dialog = document.createElement('dialog');
      dialog.className = 'figure-dialog';
      const close = document.createElement('button');
      close.textContent = '关闭放大图';
      const img = button.querySelector('img').cloneNode();
      img.loading = 'eager';
      dialog.append(close, img);
      document.body.append(dialog);
      close.addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', e => {if(e.target === dialog) dialog.close();});
      dialog.addEventListener('close', () => {dialog.remove();button.focus();});
      dialog.showModal();
    });
  });
  const mul = (a,b) => a.map(row => b[0].map((_,j) => row.reduce((s,x,k)=>s+x*b[k][j],0)));
  const transpose = a => a[0].map((_,j)=>a.map(row=>row[j]));
  const projections = [
    {q:[[1,0],[0,1],[0,0],[0,0]],k:[[1,0],[0,1],[0,0],[0,0]],v:[[0,0],[0,0],[1,0],[0,1]]},
    {q:[[0,0],[0,0],[1,0],[0,1]],k:[[0,0],[0,0],[1,0],[0,1]],v:[[1,0],[0,1],[0,0],[0,0]]}
  ];
  const fmt = x => x === -Infinity ? '−∞' : Number(x).toFixed(3);
  function matrix(label, a, heat=false) {
    return `<div class="matrix-card"><h4>${label}</h4><div class="table-wrap"><table><tbody>${a.map(row=>'<tr>'+row.map(x=>`<td ${heat ? `style="background:rgba(64,143,214,${Number.isFinite(x)?Math.min(.85,Math.max(.06,x)):.02})"`:''}>${fmt(x)}</td>`).join('')+'</tr>').join('')}</tbody></table></div></div>`;
  }
  document.querySelectorAll('[data-visualization="attention"]').forEach(lab => {
    lab.innerHTML = `<div class="lab-heading"><span class="lab-badge">CALCULATION LAB</span><h3>把注意力算出来</h3><p>教学输入为 3 个位置、4 维表示，每头 2 维。投影矩阵使用下面给定的数值；实际模型通过训练学习这些参数。</p></div>
      <div class="lab-controls"><label>观察查询 <select class="query"><option value="0">位置 1</option><option value="1">位置 2</option><option value="2">位置 3</option></select></label><label>注意力头 <select class="head"><option value="0">Head 1</option><option value="1">Head 2</option></select></label><label><input type="checkbox" class="scaled" checked> 除以 √dₖ</label><label><input type="checkbox" class="causal"> 因果 mask</label><button class="reset" type="button">重置输入</button></div>
      <div class="lab-input"><h4>输入 X · 点击数值修改</h4><div class="input-grid"></div></div>
      <div class="flow-strip"><span class="q-color">Q = XW<sup>Q</sup></span><b>×</b><span class="k-color">Kᵀ</span><b>→</b><span>Scale / Mask</span><b>→</b><span>softmax</span><b>→</b><span class="v-color">× V</span></div>
      <div class="attention-graph" aria-label="查询位置到三个值向量的加权连接"></div><div class="lab-results" aria-live="polite"></div><details><summary>查看 Q/K/V、各投影矩阵与多头输出</summary><div class="lab-matrices"></div></details>`;
    const initial = [[1,0,1,0],[0,1,0,2],[1,1,2,1]];
    const grid = lab.querySelector('.input-grid');
    initial.forEach((row,i) => {
      const label = document.createElement('span');label.textContent = `位置 ${i+1}`;grid.append(label);
      row.forEach((x,j)=>{const input=document.createElement('input');input.type='number';input.min='-10';input.max='10';input.step='.25';input.value=x;input.setAttribute('aria-label',`X 位置 ${i+1} 维度 ${j+1}`);grid.append(input);});
    });
    function update() {
      const inputs = [...grid.querySelectorAll('input')];
      const x = initial.map((row,i)=>row.map((_,j)=>Math.max(-10,Math.min(10,Number(inputs[i*4+j].value)||0))));
      const selected = Number(lab.querySelector('.query').value), head = Number(lab.querySelector('.head').value);
      const scale = lab.querySelector('.scaled').checked ? Math.sqrt(2) : 1;
      const causal = lab.querySelector('.causal').checked;
      const heads = projections.map(p=>{
        const q=mul(x,p.q),k=mul(x,p.k),v=mul(x,p.v);
        const logits=mul(q,transpose(k)).map((r,i)=>r.map((s,j)=>causal && j>i ? -Infinity:s/scale));
        const weights=logits.map(row=>{const max=Math.max(...row);const exps=row.map(s=>Math.exp(s-max));const sum=exps.reduce((a,b)=>a+b,0);return exps.map(e=>e/sum);});
        return {q,k,v,logits,weights,z:mul(weights,v)};
      });
      const h=heads[head], weights=h.weights[selected];
      const concat = heads[0].z.map((row,i)=>[...row,...heads[1].z[i]]);
      lab.querySelector('.lab-results').innerHTML=matrix('分数 S · 行=查询 / 列=键',h.logits)+matrix('权重 A = softmax(S)',h.weights,true)+`<div class="output-card"><span>当前查询的输出 z</span><strong>[${h.z[selected].map(fmt).join(', ')}]</strong><p>权重和 = ${weights.reduce((a,b)=>a+b,0).toFixed(3)} · 形状：Q/K/V ∈ ℝ³ˣ²，A ∈ ℝ³ˣ³，Z ∈ ℝ³ˣ²</p></div>`;
      const p=projections[head];
      lab.querySelector('.lab-matrices').innerHTML=matrix('Q',h.q)+matrix('K',h.k)+matrix('V',h.v)+matrix('W<sup>Q</sup> · 4 × 2',p.q)+matrix('W<sup>K</sup> · 4 × 2',p.k)+matrix('W<sup>V</sup> · 4 × 2',p.v)+matrix('Concat(Z₁,Z₂) · 3 × 4',concat)+`<p class="matrix-note">此演示令 W<sup>O</sup> = I₄，因此最终输出等于拼接结果。实际多头注意力的 W<sup>O</sup> 通过训练学习。原论文 base 使用 8 头，d_model=512，dₖ=dᵥ=64。</p>`;
      const colors=['#69a9f3','#e3b454','#55b898'];
      lab.querySelector('.attention-graph').innerHTML=`<svg viewBox="0 0 760 220" role="img" aria-label="位置 ${selected+1} 的注意力权重 ${weights.map(fmt).join(', ')}"><rect x="15" y="75" width="125" height="60" rx="12" fill="#213950"/><text x="77" y="111" text-anchor="middle" fill="white">Q · 位置 ${selected+1}</text>${weights.map((w,j)=>{const y=25+j*70;return `<path d="M140 105 C270 105 260 ${y+25} 405 ${y+25}" fill="none" stroke="${colors[j]}" stroke-width="${2+w*12}" opacity="${w===0?.18:.85}"/><text x="270" y="${y+15}" fill="currentColor">${fmt(w)}</text><rect x="405" y="${y}" width="320" height="50" rx="10" fill="${colors[j]}" fill-opacity=".17" stroke="${colors[j]}"/><text x="565" y="${y+30}" text-anchor="middle" fill="currentColor">位置 ${j+1} · V=[${h.v[j].map(fmt).join(', ')}]</text>`;}).join('')}</svg>`;
    }
    lab.addEventListener('input',update);
    lab.addEventListener('change',update);
    lab.querySelector('.reset').addEventListener('click',()=>{[...grid.querySelectorAll('input')].forEach((input,i)=>input.value=initial.flat()[i]);update();});
    update();
  });
  document.querySelectorAll('[data-visualization="transformer"]').forEach(lab => {
    const nodes=[
      ['input',70,500,'输入嵌入 + 位置编码','输入词向量乘 √d_model 后与位置编码相加。位置编码提供序列顺序线索。'],
      ['self',70,390,'Encoder self-attention','Q、K、V 均来自编码器上一层表示；各位置可读取完整输入序列。'],
      ['norm1',70,320,'Add & Norm','原论文采用 post-norm：LayerNorm(x + Sublayer(x))；残差分支绕过该子层。'],
      ['ffn',70,220,'Position-wise FFN','每个位置共享同一个两层网络：max(0, xW₁+b₁)W₂+b₂。base 中 512 → 2048 → 512。'],
      ['norm2',70,140,'Add & Norm · 编码器输出','每个编码器层包含自注意力和 FFN；base 堆叠 6 层。最终表示传给各解码器层作 K/V。'],
      ['target',475,500,'右移目标嵌入 + 位置','训练输入使用右移的目标序列，预测对应位置的下一个词；与因果 mask 配合。'],
      ['masked',475,410,'Masked self-attention','Q/K/V 来自解码器表示。softmax 前将未来位置的 logits 设为 −∞，使其权重为 0。'],
      ['norm3',475,350,'Add & Norm','残差与 LayerNorm 保存当前位置的信息并规范化表示；原论文的归一化位于残差相加之后。'],
      ['cross',475,275,'Encoder–decoder attention','Q 来自解码器上一子层；K/V 来自编码器最终输出，连接输入语句与目标语句。'],
      ['norm4',475,215,'Add & Norm','解码器的交叉注意力子层同样使用残差连接与 LayerNorm。'],
      ['dffn',475,140,'FFN → Add & Norm','逐位置前馈变换后作残差相加与归一化；base 解码器堆叠 6 层。'],
      ['output',475,40,'Linear → Softmax → 词分布','解码器输出投影到词表后，softmax 得到下一词概率。推理时按自回归顺序生成。']
    ];
    lab.innerHTML=`<div class="lab-heading"><span class="lab-badge">ARCHITECTURE MAP</span><h3>顺着数据流阅读 Transformer</h3><p>点击模块查看它的输入、作用与张量关系。此教学图按 Figure 1 重绘，重复层与残差分支的完整连线见上方原图。</p></div><div class="architecture-map"><svg viewBox="0 0 820 580" role="group" aria-label="交互 Transformer 架构图"><defs><marker id="arch-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#7892ad"/></marker></defs><rect x="50" y="120" width="310" height="350" rx="18" fill="#65a9ff" fill-opacity=".06" stroke="#8aa6bf" stroke-dasharray="5 5"/><rect x="455" y="120" width="310" height="350" rx="18" fill="#55b898" fill-opacity=".06" stroke="#8aa6bf" stroke-dasharray="5 5"/><text x="65" y="110" fill="currentColor">Encoder × 6</text><text x="480" y="110" fill="currentColor">Decoder × 6</text>${[[0,1],[1,2],[2,3],[3,4],[5,6],[6,7],[7,8],[8,9],[9,10],[10,11]].map(([a,b])=>`<path d="M${nodes[a][1]+135} ${nodes[a][2]} L${nodes[b][1]+135} ${nodes[b][2]+44}" fill="none" stroke="#7892ad" stroke-width="2" marker-end="url(#arch-arrow)"/>`).join('')}<path d="M340 162 L400 162 L400 297 L475 297" fill="none" stroke="#55b898" stroke-width="3" marker-end="url(#arch-arrow)"/><text x="382" y="244" fill="currentColor">K/V</text>${nodes.map(([id,x,y,text])=>`<g class="arch-node" data-node="${id}" role="button" tabindex="0" aria-label="${text}"><rect x="${x}" y="${y}" width="270" height="44" rx="9" fill="${id==='cross'?'#195c4a':id==='masked'?'#604919':'#243c55'}" stroke="#91b0cf"/><text x="${x+135}" y="${y+28}" fill="white" text-anchor="middle">${text}</text></g>`).join('')}</svg></div><div class="architecture-detail" aria-live="polite">选择一个模块，查看计算说明。</div>`;
    function select(g) {
      lab.querySelectorAll('.arch-node').forEach(n=>n.classList.toggle('selected',n===g));
      const n=nodes.find(n=>n[0]===g.dataset.node);
      const detail=lab.querySelector('.architecture-detail');
      detail.replaceChildren();
      const title=document.createElement('strong');title.textContent=n[3];
      const body=document.createElement('p');body.textContent=n[4];detail.append(title,body);
    }
    lab.querySelectorAll('.arch-node').forEach(g=>{g.addEventListener('click',()=>select(g));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(g);}});});
  });
})();
