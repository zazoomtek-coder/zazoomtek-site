// Poll YouTube every five minutes; publish only in the three Europe/Rome slots.
async function hasActiveRun(env, repo, workflow) {
  const headers = {
    Authorization: "Bearer " + env.GITHUB_TOKEN,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ZazoomTek-Cloudflare-Cron",
  };
  for (const status of ["queued", "in_progress"]) {
    const url = "https://api.github.com/repos/" + repo +
      "/actions/workflows/" + workflow + "/runs?branch=main&status=" +
      status + "&per_page=1";
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error("Cannot check active editorial runs: HTTP " +
        response.status + " " + (await response.text()).slice(0, 200));
    }
    const data = await response.json();
    if (Number(data.total_count || 0) > 0) return true;
  }
  return false;
}

async function dispatchWorkflow(env, repo, workflow, inputs = {}) {
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
    body: JSON.stringify({ ref: "main", inputs }),
  });
  if (response.status !== 204) {
    throw new Error("GitHub dispatch failed for " + workflow + ": HTTP " +
      response.status + " " + (await response.text()).slice(0, 250));
  }
}

function romeClock(timestamp) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Rome",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(timestamp));
  const hour = parts.find((part) => part.type === "hour")?.value || "00";
  const minute = parts.find((part) => part.type === "minute")?.value || "00";
  return hour + ":" + minute;
}

export default {
  async scheduled(event, env) {
    if (!env.GITHUB_TOKEN) throw new Error("Missing GITHUB_TOKEN secret");

    const repo = env.GITHUB_REPO || "zazoomtek-coder/zazoomtek-site";
    const collector = env.GITHUB_COLLECT_WORKFLOW || "editorial-collect.yml";
    const publisher = env.GITHUB_PUBLISH_WORKFLOW || "editorial-publish.yml";
    const localTime = romeClock(event.scheduledTime);

    // Intake is independent from publication and runs on every five-minute tick.
    if (await hasActiveRun(env, repo, collector)) {
      console.log("Five-minute intake skipped: collector is already queued or running");
    } else {
      await dispatchWorkflow(env, repo, collector);
      console.log("YouTube video + Community collection dispatched", {
        scheduledTime: new Date(event.scheduledTime).toISOString(),
        localTime,
      });
    }

    // A deploy can only be requested at these exact Europe/Rome times.
    if (["12:30", "16:00", "19:30"].includes(localTime)) {
      if (await hasActiveRun(env, repo, publisher)) {
        console.log("Release slot skipped: publisher is already queued or running", localTime);
      } else {
        await dispatchWorkflow(env, repo, publisher, { release_slot: localTime });
        console.log("Authorized editorial release dispatched", { localTime });
      }
    }
  },
};
