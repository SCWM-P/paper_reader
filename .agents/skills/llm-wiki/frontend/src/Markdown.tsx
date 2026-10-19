import {useEffect,useId,useState} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

function Mermaid({code}:{code:string}){
 const id=useId().replace(/[^a-zA-Z0-9]/g,'');
 const [svg,setSvg]=useState(''),[error,setError]=useState('');
 useEffect(()=>{let cancelled=false;
  import('mermaid').then(async({default:m})=>{
   m.initialize({startOnLoad:false,securityLevel:'strict',theme:document.documentElement.classList.contains('dark')?'dark':'neutral'});
   const result=await m.render('mermaid'+id,code);
   if(!cancelled)setSvg(result.svg);
  }).catch(e=>{if(!cancelled)setError(String(e))});
  return()=>{cancelled=true};
 },[code,id]);
 return error?<pre className="warning">{error}</pre>:<div className="mermaid" dangerouslySetInnerHTML={{__html:svg}}/>;
}
function wikilinks(){
 return (tree:any)=>{
  function walk(node:any){
   if(!node.children||node.type==='link'||node.type==='code'||node.type==='inlineCode')return;
   node.children=node.children.flatMap((child:any)=>{
    if(child.type!=='text'){walk(child);return [child]}
    const text=child.value;const re=/\[\[([^\]|\n]+)(?:\|([^\]\n]*))?\]\]/g;
    const result:any[]=[];let end=0;let match;
    while((match=re.exec(text))){
     if(match.index>end)result.push({type:'text',value:text.slice(end,match.index)});
     result.push({type:'link',url:'/wiki-link?target='+encodeURIComponent(match[1]),children:[{type:'text',value:match[2]||match[1]}]});
     end=re.lastIndex;
    }
    if(end<text.length)result.push({type:'text',value:text.slice(end)});
    return result.length?result:[child];
   });
  }walk(tree);
 };
}
export default function Markdown({body,targets={},onOpen}:{body:string;targets?:Record<string,string>;onOpen:(ref:string)=>void}){
 return <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm,remarkMath,wikilinks]} rehypePlugins={[rehypeKatex]}
 components={{
  a:({href,children})=>{if(href?.startsWith('/wiki-link?')){
   const target=new URLSearchParams(href.split('?')[1]).get('target')||'';
   return <button className="inline-link" onClick={()=>onOpen(targets[target]||target)}>{children}</button>;
  }return <a href={href} target="_blank" rel="noreferrer">{children}</a>},
  code:({className,children,...props})=>className==='language-mermaid'?<Mermaid code={String(children).trim()}/>:<code className={className} {...props}>{children}</code>,
 }}>{body}</ReactMarkdown></div>;
}

