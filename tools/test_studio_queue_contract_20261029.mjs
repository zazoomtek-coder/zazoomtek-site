import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const source=readFileSync("functions/api/studio/[[path]].js","utf8");
const {onRequest}=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
const base="https://zazoomtek.it";
const repo="zazoomtek-coder/zazoomtek-site";
const state=new Map([
 ["data/studio_posts.json",{posts:[]}],
 ["data/studio_overrides.json",{overrides:{}}],
 ["data/studio_v2_drafts.json",{drafts:{}}]
]);
let seq=0;
const initialFetch=globalThis.fetch;
globalThis.fetch=async(url,opts={})=>{
 const address=new URL(url);
 if(address.hostname!=="api.github.com")throw Error("Unexpected network: "+address.hostname);
 const path=decodeURIComponent(address.pathname);
 if(path==="/user")return Response.json({login:"zazoomtek-coder",id:333682421});
 if(path==="/repos/"+repo)return Response.json({full_name:repo,permissions:{push:true}});
 const marker="/repos/"+repo+"/contents/";
 if(!path.startsWith(marker))throw Error("Unexpected GitHub endpoint "+path);
 const filename=path.slice(marker.length);
 if(opts.method==="PUT"){
  const document=JSON.parse(opts.body);
  const current=state.get(filename);
  if(!current)return Response.json({message:"Not Found"},{status:404});
  assert.equal(document.sha,"sha-"+seqFor(filename));
  state.set(filename,JSON.parse(Buffer.from(document.content,"base64").toString("utf8")));
  version.set(filename,seqFor(filename)+1);
  return Response.json({content:{sha:"sha-"+seqFor(filename)}});
 }
 if(!state.has(filename))return Response.json({message:"Not Found"},{status:404});
 return Response.json({sha:"sha-"+seqFor(filename),content:Buffer.from(JSON.stringify(state.get(filename))).toString("base64")});
};
const version=new Map();
const seqFor=path=>version.get(path)||0;
const env={STUDIO_SESSION_SECRET:"test-secret-32-bytes-cryptographically-long",ASSETS:{fetch:async request=>{
 if(new URL(request.url).pathname==="/studio-v2/catalog.json")return Response.json({posts:[]});
 throw Error("Unexpected asset "+request.url);
}}};
const doRequest=(path,method="GET",body=null,cookie="")=>onRequest({
 env,
 request:new Request(base+"/api/studio/"+path,{
  method,headers:{
   ...(method==="POST"?{"Origin":base,"Content-Type":"application/json"}:{}),
   ...(cookie?{"Cookie":cookie}:{})
  },
  ...(body?{body:JSON.stringify(body)}:{})
 })
});
const token="github_pat_valid_token_for_test_0123456";
const login=await doRequest("login","POST",{token});
assert.equal(login.status,200,await login.text());
const cookie=login.headers.get("set-cookie").split(";")[0];
let checked=await doRequest("session","GET",null,cookie);
assert.equal((await checked.json()).authenticated,true);
const article={
 slug:"test-studio-in-coda",title:"Test del flusso corretto di pubblicazione Studio",
 category:"news-tech",image:"/assets/uploads/test-studio-in-coda/abc.jpg",
 body:[{type:"paragraph",text:"Questo paragrafo contiene una descrizione di test sufficientemente lunga per verificare il salvataggio dei contenuti editoriali. ".repeat(4)}],
 author:"Redazione ZazoomTek",score:"",platform:"",pros:[],cons:[]
};
let first=await doRequest("v2-save","POST",{mode:"publish",creating:true,record:article},cookie);
assert.equal(first.status,200,await first.text());
let firstResult=await first.json();
assert.equal(firstResult.status,"queued");
assert.equal(firstResult.record.title,article.title);
assert.equal(state.get("data/studio_posts.json").posts.length,1);
article.title="Test del flusso corretto di pubblicazione Studio aggiornato";
let second=await doRequest("v2-save","POST",{mode:"publish",creating:false,record:article},cookie);
assert.equal(second.status,200,await second.text());
assert.equal(state.get("data/studio_posts.json").posts.length,1);
assert.equal(state.get("data/studio_posts.json").posts[0].title,article.title);
let queue=await doRequest("v2-pending","GET",null,cookie);
assert.equal(queue.status,200,await queue.text());
assert.equal((await queue.json()).posts.length,1);
assert.equal(state.get("data/studio_overrides.json").overrides["test-studio-in-coda"],undefined);
let draft=await doRequest("v2-save","POST",{mode:"draft",record:{...article,title:"Bozza non pubblicata"}},cookie);
assert.equal(draft.status,200,await draft.text());
assert.equal(state.get("data/studio_posts.json").posts.length,1);
assert.equal(state.get("data/studio_v2_drafts.json").drafts[article.slug].record.title,"Bozza non pubblicata");
globalThis.fetch=initialFetch;
console.log("STUDIO CONTRACT PASS: auth, queue, preview record, update without duplicates, draft isolation, no deploy");
