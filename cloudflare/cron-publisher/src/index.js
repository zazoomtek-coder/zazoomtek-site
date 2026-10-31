// Cloudflare Cron controls scheduling; GitHub only imports, builds and deploys.
// GITHUB_TOKEN is a secret configured in Cloudflare, never checked into Git.
const slots = [12*60+30, 16*60, 19*60+30];
const formatter = new Intl.DateTimeFormat("en-GB", {
  timeZone:"Europe/Rome", year:"numeric",month:"2-digit",day:"2-digit",
  hour:"2-digit", minute:"2-digit", hourCycle:"h23"
});
function localClock(timestamp) {
  const values=Object.fromEntries(formatter.formatToParts(new Date(timestamp))
    .filter(p=>p.type!=="literal").map(p=>[p.type,p.value]));
  return {date:`${values.year}-${values.month}-${values.day}`,
    minutes:Number(values.hour)*60+Number(values.minute)};
}
function currentSlot(clock) {
  // Start 15 minutes before slot. Retry every five minutes for 60 minutes
  // after slot, never prematurely discard pending articles.
  return slots.find(m=>clock.minutes>=m-15 && clock.minutes<m+60);
}
const headers=(token)=>({
  Authorization:"Bearer "+token,Accept:"application/vnd.github+json",
  "X-GitHub-Api-Version":"2022-11-28",
  "User-Agent":"ZazoomTek-Cloudflare-Cron"
});
export default {
  async scheduled(event,env) {
    const clock=localClock(event.scheduledTime);
    const slot=currentSlot(clock);
    if(slot===undefined) return;
    if(!env.GITHUB_TOKEN) throw Error("Missing Cloudflare Worker GITHUB_TOKEN secret");
    const repo=env.GITHUB_REPO||"zazoomtek-coder/zazoomtek-site";
    const workflow=env.GITHUB_WORKFLOW||"editorial-publish.yml";
    const base="https://api.github.com/repos/"+repo;
    const name=clock.date+"T"+String(Math.floor(slot/60)).padStart(2,"0")+
      ":"+String(slot%60).padStart(2,"0")+":00";
    // Do not dispatch if the release receipt already confirms this slot.
    // When no receipt exists, safely retry; the GitHub gate rechecks the state.
    const receipt=await fetch(base+"/contents/data/editorial_release_state.json?ref=main",
      {headers:headers(env.GITHUB_TOKEN)});
    if(receipt.ok) {
      const entry=await receipt.json();
      const raw=atob(String(entry.content||"").replace(/\s/g,""));
      const state=JSON.parse(raw);
      if(String(state.slot||"").startsWith(name)) {
        console.log("Already published; skip retry",name);
        return;
      }
    } else if(receipt.status!==404) {
      throw Error("Cannot check release receipt: HTTP "+receipt.status);
    }
    const response=await fetch(base+"/actions/workflows/"+workflow+"/dispatches",{
      method:"POST",
      headers:{...headers(env.GITHUB_TOKEN),"Content-Type":"application/json"},
      body:JSON.stringify({ref:"main"})
    });
    if(response.status!==204) throw Error("Workflow dispatch failed: HTTP "+
      response.status+" "+(await response.text()).slice(0,220));
    console.log("Workflow dispatch requested",name,"clock",clock.minutes);
  }
};
