import {useEffect,useRef,useState} from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import {ZoomIn,ZoomOut,Maximize2,ExternalLink} from 'lucide-react';
import {api,labels} from './types';
import type {Row} from './types';

const colors:Record<string,string>={concept:'#7c83db',entity:'#51a48e',source:'#d2a456',comparison:'#c17ca5',synthesis:'#718caa',query:'#c88766',overview:'#777777',question:'#c28a60'};
export default function GraphView({onOpen}:{onOpen:(ref:string,id?:string)=>void}){
 const container=useRef<HTMLDivElement>(null),renderer=useRef<Sigma|null>(null);
 const [data,setData]=useState<any>(),[selected,setSelected]=useState<any>(),[type,setType]=useState(''),[focus,setFocus]=useState<string>(),[error,setError]=useState(''),[counts,setCounts]=useState({nodes:0,edges:0});
 useEffect(()=>{api('graph?limit=1000').then(setData).catch(e=>setError(e.message))},[]);
 useEffect(()=>{
  if(!data||!container.current)return;
  const graph=new Graph({type:'undirected',multi:false});
  const near=new Set<string>(focus?[focus]:[]);
  if(focus)for(const e of data.edges)if(e.source===focus||e.target===focus){near.add(e.source);near.add(e.target)}
  const visible=data.nodes.filter((n:Row)=>(!type||n.type===type)&&(!focus||near.has(n.id)));
  visible.forEach((n:Row,i:number)=>graph.addNode(n.id,{...n,recordType:n.type,type:'circle',label:n.title,x:Math.cos(i*2.399)*Math.sqrt(i+1),y:Math.sin(i*2.399)*Math.sqrt(i+1),size:n.type==='source'?5:7,color:colors[n.type]||'#888'}));
  data.edges.forEach((e:any)=>{
   if(graph.hasNode(e.source)&&graph.hasNode(e.target)&&e.source!==e.target&&!graph.hasEdge(e.source,e.target))graph.addEdge(e.source,e.target,{size:.6,color:'#aaa5',label:e.label});
  });
  if(graph.order>1)forceAtlas2.assign(graph,{iterations:180,settings:{gravity:.8,scalingRatio:8,slowDown:8,barnesHutOptimize:true}});
  setCounts({nodes:graph.order,edges:graph.size});
  let sigma:Sigma;
  try{
   setError('');
   sigma=new Sigma(graph,container.current,{renderEdgeLabels:false,labelFont:'Geist Variable, sans-serif',labelSize:12,
    labelColor:{color:document.documentElement.classList.contains('dark')?'#ddd':'#444'},defaultEdgeType:'line',labelDensity:.25});
  }catch(e){setError('图谱需要浏览器 WebGL：'+String(e));return}
  renderer.current=sigma;
  let dragging:string|null=null,moved=false;
  sigma.on('clickNode',({node})=>{if(!moved)setSelected(data.nodes.find((n:Row)=>n.id===node));moved=false});
  sigma.on('downNode',e=>{dragging=e.node;moved=false;sigma.getCamera().disable();if(!sigma.getCustomBBox())sigma.setCustomBBox(sigma.getBBox())});
  sigma.getMouseCaptor().on('mousemovebody',e=>{
   if(!dragging)return;moved=true;const p=sigma.viewportToGraph(e);graph.setNodeAttribute(dragging,'x',p.x);graph.setNodeAttribute(dragging,'y',p.y);e.preventSigmaDefault();e.original.preventDefault();e.original.stopPropagation();
  });
  sigma.getMouseCaptor().on('mouseup',()=>{dragging=null;sigma.getCamera().enable()});
  return()=>{sigma.kill();renderer.current=null};
 },[data,type,focus]);
 const neighbors=selected?data?.edges.filter((e:any)=>e.source===selected.id||e.target===selected.id).map((e:any)=>e.source===selected.id?e.target:e.source):[];
 return <div className="graph-page">
  <div className="page-heading"><div><span className="eyebrow">KNOWLEDGE GRAPH</span><h1>知识图谱</h1><p>节点来自真实记录，关系来自明确引用。</p></div>
   <select aria-label="节点类型" value={type} onChange={e=>setType(e.target.value)}><option value="">全部类型</option>{Object.entries(labels).filter(([k])=>k!=='question').map(([k,v])=><option key={k} value={k}>{v}</option>)}</select>
  </div>
  {error&&<div className="warning">{error}</div>}
  {data?.errors?.length>0&&<div className="warning">存在 {data.errors.length} 项引用错误，请运行 check。</div>}
  <div className="graph-canvas" ref={container}/>
  <div className="graph-tools">
   <button aria-label="放大图谱" onClick={()=>renderer.current?.getCamera().animatedZoom()}><ZoomIn size={17}/></button>
   <button aria-label="缩小图谱" onClick={()=>renderer.current?.getCamera().animatedUnzoom()}><ZoomOut size={17}/></button>
   <button aria-label="重置图谱" onClick={()=>{setFocus(undefined);renderer.current?.getCamera().animatedReset()}}><Maximize2 size={17}/></button>
   <span>当前 {counts.nodes} 个节点 · {counts.edges} 条连线 · 全库 {data?.nodes.length??0} 个节点</span>
  </div>
  {selected&&<div className="graph-selection"><span className="eyebrow">{labels[selected.type]}</span><h3>{selected.title}</h3>
   <button className="primary" onClick={()=>onOpen(selected.record,selected.item_id)}>打开页面 <ExternalLink size={14}/></button>
   <button onClick={()=>{setFocus(selected.id);setType('')}}>仅查看邻居</button>
   <h4>相邻页面</h4>{[...new Set(neighbors)].slice(0,20).map((id:any)=>{const n=data.nodes.find((x:Row)=>x.id===id);return n&&<button className="text-link" key={id} onClick={()=>setSelected(n)}>{n.title}</button>})}
  </div>}
 </div>;
}

