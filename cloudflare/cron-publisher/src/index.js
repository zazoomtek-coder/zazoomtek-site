// Cloudflare Cron: trigger the existing protected publishing workflow.
// A GitHub PAT with Actions:write for this repository must be configured
// as the GITHUB_TOKEN Worker secret, never committed to source control.
const SLOTS = new Set(["12:30", "16:00", "19:30"]);
const ROME_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Rome", hour: "2-digit", minute: "2-digit",
  hourCycle: "h23",
});
function italianTime(timestamp) {
  const parts = ROME_CLOCK.formatToParts(new Date(timestamp));
  const hour = parts.find((p) => p.type === "hour")?.value;
  const minute = parts.find((p) => p.type === "minute")?.value;
  return hour + ":" + minute;
}
export default {
  async scheduled(event, env) {
    const slot = italianTime(event.scheduledTime);
    if (!SLOTS.has(slot)) {
      console.log("Skipping UTC candidate outside Italian slots", slot);
      return;
    }
    if (!env.GITHUB_TOKEN) throw new Error("Missing GITHUB_TOKEN secret");
    const repo = env.GITHUB_REPO || "zazoomtek-coder/zazoomtek-site";
    const workflow = env.GITHUB_WORKFLOW || "editorial-publish.yml";
    const endpoint = "https://api.github.com/repos/" + repo +
      "/actions/workflows/" + workflow + "/dispatches";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: "Bearer " + env.GITHUB_TOKEN,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ZazoomTek-Cloudflare-Cron",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    });
    if (response.status !== 204) {
      throw new Error("GitHub workflow dispatch failed: HTTP " + response.status +
        " " + (await response.text()).slice(0,250));
    }
    console.log("GitHub editorial dispatch accepted", slot, "Europe/Rome");
  },
};
