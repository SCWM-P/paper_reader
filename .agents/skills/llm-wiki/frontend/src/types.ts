export type Data = Record<string, any>;
export type Row = {record:string;id:string;type:string;title:string;domain:string;tags:string[];sha256:string};
export type Document = {record:string;data:Data;item?:Data;body:string;sha256:string;draft?:boolean;
  backlinks?:{record:string;title:string}[];links?:Data[];link_targets?:Record<string,string>;errors?:Data[];
  completeness?:Data;view?:Data;note_url?:string;pdf_url?:string};
export const labels:Record<string,string>={concept:'概念',entity:'实体',source:'论文',query:'研究议题',comparison:'比较',synthesis:'综合',overview:'概览',question:'实际问答'};
export async function api<T=any>(path:string, body?:unknown):Promise<T>{
 const response=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',
 headers:{'x-wiki-token':document.querySelector<HTMLMetaElement>('meta[name="wiki-token"]')?.content||'',...(body===undefined?{}:{'Content-Type':'application/json'})},
 body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json();
 if(!response.ok)throw new Error((response.status===409?'保存冲突：':'')+(data.reason||response.statusText));
 return data;
}

