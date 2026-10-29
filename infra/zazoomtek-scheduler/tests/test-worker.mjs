import {decide,dispatch,localParts} from "../src/worker.js";
import assert from "node:assert/strict";

const utc=str=>Date.parse(str);
assert.deepEqual(localParts(utc("2026-10-29T18:21:00Z")),{hour:19,minute:21});
assert.equal(decide(utc("2026-10-29T18:21:00Z")).kind,"release");
assert.equal(decide(utc("2026-10-29T18:26:00Z")).kind,"release");
assert.equal(decide(utc("2026-10-29T18:33:00Z")).kind,"release");
assert.equal(decide(utc("2026-10-29T18:38:00Z")).kind,"release");
assert.equal(decide(utc("2026-10-29T18:20:00Z")).kind,"intake");
assert.equal(decide(utc("2026-10-29T18:30:00Z")).kind,"none");
assert.equal(decide(utc("2026-10-29T08:10:00Z")).kind,"intake");
// Winter (after DST) and summer slots must both be correct.
assert.equal(decide(utc("2026-10-30T18:21:00Z")).kind,"release");
assert.equal(decide(utc("2027-06-01T17:21:00Z")).kind,"release");
assert.equal(decide(utc("2027-06-01T18:21:00Z")).kind,"none");
assert.equal(decide(utc("2027-06-01T10:21:00Z")).kind,"release");
let calls=[];
const fake=async (url,args)=>{calls.push({url,args});return{status:204};};
assert.equal(await dispatch("editorial-publish.yml","FAKE_TEST_TOKEN",fake),204);
assert.equal(calls.length,1);
assert.match(calls[0].url,/editorial-publish\.yml\/dispatches$/);
assert.equal(JSON.parse(calls[0].args.body).ref,"main");
assert.match(calls[0].args.headers.Authorization,/^Bearer FAKE_TEST_TOKEN$/);
assert.equal(await dispatch("editorial-publish.yml","FAKE_TEST_TOKEN",
 async()=>({status:200,json:async()=>({workflow_run_id:123})})),200);
await assert.rejects(dispatch("editorial-collect.yml","",fake),/Missing secret/);
await assert.rejects(dispatch("editorial-collect.yml","x",async()=>({status:401,text:async()=>"Denied"})),/HTTP 401/);
console.log("INDEPENDENT CLOUDFLARE SCHEDULER TESTS PASSED: timezone, DST, retry, token, API");
