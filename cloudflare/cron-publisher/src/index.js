// Cloudflare Cron: one exact dispatch candidate for each Europe/Rome slot.
// No retry loop, recovery window, polling, or repeated dispatch.
const ALLOWED_SLOTS = new Set(["12:30", "16:00", "19:30"]);

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
    const localTime = italianTime(event.scheduledTime);

    // The UTC cron list includes both DST offsets. Exactly one candidate
    // maps to each required local slot on any given date.
    if (!ALLOWED_SLOTS.has(localTime)) {
      console.log("Skipped non-slot UTC candidate", {
        scheduledTime: new Date(event.scheduledTime).toISOString(),
        localTime,
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
      body: JSON.stringify({ ref: "main", inputs: { release_slot: localTime } }),
    });

    if (response.status !== 204) {
      throw new Error(
        "GitHub workflow dispatch failed: HTTP " + response.status +
        " " + (await response.text()).slice(0, 250)
      );
    }

    console.log("Single editorial preflight dispatch accepted", localTime, "Europe/Rome");
  },
};
