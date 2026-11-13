// Cloudflare Cron: one preflight dispatch 15 minutes before each Europe/Rome slot.
// No retry loop, recovery window, polling, or repeated dispatch.
const PREFLIGHT_TO_SLOT = new Map([
  ["12:15", "12:30"],
  ["15:45", "16:00"],
  ["19:15", "19:30"],
]);

const ROME_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Rome",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function italianTime(timestamp) {
  return ROME_CLOCK.format(new Date(timestamp));
}

export default {
  async scheduled(event, env) {
    const preflightTime = italianTime(event.scheduledTime);
    const releaseSlot = PREFLIGHT_TO_SLOT.get(preflightTime);

    // The UTC cron list includes both DST offsets. Exactly one candidate
    // maps to each preflight time on any given date.
    if (!releaseSlot) {
      console.log("Skipped non-preflight UTC candidate", {
        scheduledTime: new Date(event.scheduledTime).toISOString(),
        preflightTime,
      });
      return;
    }

    if (!env.GITHUB_TOKEN) {
      throw new Error("Missing GITHUB_TOKEN secret");
    }

    const repo = env.GITHUB_REPO || "zazoomtek-coder/zazoomtek-site";
    const workflow = env.GITHUB_WORKFLOW || "editorial-publish.yml";
    const endpoint =
      "https://api.github.com/repos/" + repo +
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
      body: JSON.stringify({ ref: "main", inputs: { release_slot: releaseSlot } }),
    });

    if (response.status !== 204) {
      throw new Error(
        "GitHub workflow dispatch failed: HTTP " + response.status +
        " " + (await response.text()).slice(0, 250)
      );
    }

    console.log("Editorial preflight dispatch accepted", {
      preflightTime,
      releaseSlot,
      timezone: "Europe/Rome",
    });
  },
};
