// Cloudflare backup scheduler for ZazoomTek — INDEPENDENT of GitHub cron.
// Disabled until explicitly deployed and configured with a GitHub Actions token.
// Sends dispatches; does NOT itself alter the site or bypass the release gate.
// A GitHub 204 confirms accepted trigger, NOT completed import or deploy.
const GITHUB_REPO="zazoomtek-coder/zazoomtek-site";
const INTAKE="editorial-collect.yml";
const RELEASE="editorial-publish.yml";

export function localParts(instant) {
 const vals=new Intl.DateTimeFormat("en-GB",{
  timeZone:"Europe/Rome",hour12:false,hour:"2-digit",minute:"2-digit"
 }).formatToParts(new Date(instant));
 const ob=Object.fromEntries(vals.filter(x=>["hour","minute"].includes(x.type))
  .map(x=>[x.type,Number(x.value)]));
 return ob;
}

export function decide(instant) {
 const {hour,minute}=localParts(instant);
 // Run before 12:30 and 19:30, retry just AFTER the expected minute if
 // GitHub's own cron was late/dropped. The release gate is authoritative.
 if((hour===12||hour===19)&&[21,26,33,38].includes(minute))
  return {kind:"release",hour,minute};
 const active=(hour>=9&&hour<=11)||
  (hour===12&&(minute<=20||minute>=31))||
  (hour>=13&&hour<=18)||
  (hour===19&&minute<=20);
 if(active&&minute%10===0)return {kind:"intake",hour,minute};
 return {kind:"none",hour,minute};
}

export async function dispatch(workflow,token,request=fetch) {
 if(!token)throw new Error("Missing secret GITHUB_AUTOMATION_TOKEN");
 const response=await request("https://api.github.com/repos/"+GITHUB_REPO+
  "/actions/workflows/"+encodeURIComponent(workflow)+"/dispatches",{
   method:"POST",
   headers:{
    "Authorization":"Bearer "+token,
    "Accept":"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28",
    "User-Agent":"ZazoomTek-Independent-Backup-Scheduler",
    "Content-Type":"application/json"
   },body:JSON.stringify({ref:"main"})
  });
 if(response.status!==204)
  throw new Error("Dispatch failed for "+workflow+" HTTP "+response.status+
   " "+(await response.text()).slice(0,180));
 return 204;
}

export default {
 async scheduled(controller,env,ctx) {
  const slot=decide(controller.scheduledTime);
  if(slot.kind==="none")return;
  const job=slot.kind==="release"?RELEASE:INTAKE;
  ctx.waitUntil(dispatch(job,env.GITHUB_AUTOMATION_TOKEN).then(()=>{
   console.log("Backup scheduler dispatch accepted",slot.kind,
    controller.scheduledTime,"Rome",slot.hour+":"+slot.minute,
    "NOTE: 204 is not an import/deploy success receipt");
  }).catch(error=>{
   console.error("BACKUP SCHEDULER FAILED",job,String(error));
   throw error;
  }));
 }
};
