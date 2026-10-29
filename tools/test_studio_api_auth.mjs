// Full Studio HTTP API regression using a fake GitHub backend.
// No real PAT, no internet request, no Cloudflare deployment.
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
globalThis.crypto = webcrypto;
const {onRequest} = await import("../functions/api/studio/[[path]].js");

const host="https://zazoomtek.it";
const files=new Map();
const writes=[];
const slug="community-ugkxf-aembzj-nrh3uwdvfxhfshcpji31jjc";
const body=[{type:"paragraph",text:"Recensione approfondita degli occhiali intelligenti con funzioni tecniche e prove originali. ".repeat(6)}];
const record={slug,title:"DTNO.1 DT H03 Recensione | Smart glasses con fotocamera Sony, AI",
 category:"recensioni-tech",image:"/assets/uploads/"+slug+"/recensione.png",body,
 author:"Redazione ZazoomTek",platform:"Smart glasses",score:"8",pros:[],cons:[]};
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json"}});
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(String(url)),p=u.pathname;
 if(u.hostname!=="api.github.com")throw Error("Unexpected outbound hostname: "+u.hostname);
 if(p==="/user")return json({login:"zazoomtek-coder",id:1234});
 if(p==="/repos/zazoomtek-coder/zazoomtek-site")return json({full_name:"zazoomtek-coder/zazoomtek-site",permissions:{push:true}});
 const marker="/contents/";
 if(p.includes(marker)){
  const file=p.slice(p.indexOf(marker)+marker.length);
  if(opts.method==="PUT"){
   const payload=JSON.parse(opts.body);
   assert.equal(payload.branch,"editorial-queue");
   const data=JSON.parse(Buffer.from(payload.content,"base64").toString("utf8"));
   files.set(file,{sha:"mock-sha-"+(writes.length+1),content:data});
   writes.push(file);
   return json({content:{sha:files.get(file).sha}});
  }
  if(!files.has(file))return json({message:"Not Found"},404);
  const current=files.get(file);
  return json({sha:current.sha,content:Buffer.from(JSON.stringify(current.content)).toString("base64")});
 }
 throw Error("Unexpected GitHub path: "+p);
};
const env={STUDIO_SESSION_SECRET:"unit-test-secret-with-more-than-32-characters",
 ASSETS:{fetch:async()=>json({posts:[{slug,title:record.title,category:"recensioni-tech",
    image:record.image,date:"2026-10-26",published_at:"2026-10-26T10:00:00Z"}]})}};
const req=(path,method="GET",payload,headers={})=>{
 const h={...headers};
 if(method==="POST"){h.Origin=host;h["Content-Type"]="application/json"}
 return new Request(host+"/api/studio/"+path,{method,headers:h,
  body:payload!==undefined?JSON.stringify(payload):undefined});
};
const pat="github_pat_"+"x".repeat(80);
const login=await onRequest({request:req("login","POST",{token:pat}),env});
assert.equal(login.status,200);
const cookie=login.headers.get("Set-Cookie")?.split(";")[0];
assert.match(cookie||"",/^__Host-zzt-studio=/);
assert.equal((await login.json()).authenticated,true);
const unauth=await onRequest({request:req("session"),env});
assert.equal(unauth.status,401);
const session=await onRequest({request:req("session","GET",undefined,{Cookie:cookie}),env});
assert.equal(session.status,200);
assert.equal((await session.json()).login,"zazoomtek-coder");
const draft=await onRequest({request:req("v2-save","POST",{mode:"draft",record,creating:false},{Cookie:cookie}),env});
assert.equal(draft.status,200,await draft.text().catch(()=>""));
assert.deepEqual(writes,["data/studio_v2_drafts.json"]);
const savedDraft=files.get("data/studio_v2_drafts.json").content;
assert.equal(savedDraft.drafts[slug].record.title,record.title);
assert.equal(files.has("data/studio_overrides.json"),false);
const published=await onRequest({request:req("v2-save","POST",{mode:"publish",record,creating:false},{Cookie:cookie}),env});
const reply=await published.json();
assert.equal(published.status,200,JSON.stringify(reply));
assert.equal(reply.mode,"publish");
assert.equal(files.get("data/studio_overrides.json").content.overrides[slug].title,record.title);
assert.equal(files.get("data/studio_v2_drafts.json").content.drafts[slug],undefined);
assert.deepEqual(writes,["data/studio_v2_drafts.json","data/studio_overrides.json","data/studio_v2_drafts.json"]);
const forbidden=await onRequest({request:new Request(host+"/api/studio/v2-save",{method:"POST",headers:{"Origin":"https://example.org","Content-Type":"application/json",Cookie:cookie},body:JSON.stringify({mode:"draft",record})}),env});
assert.equal(forbidden.status,403);
console.log("STUDIO AUTH AND API PASS: encrypted session cookie, draft only, publish override, draft cleanup, GitHub queue only, cross-origin refused.");
