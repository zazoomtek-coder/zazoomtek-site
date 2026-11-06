// Cloudflare Cron: collect YouTube continuously and trigger protected releases
// only at the three authorized Europe/Rome publication slots.
function activeSlot(clock) {
  const [h, m] = clock.split(":").map(Number);
  for (const [hour, minute] of [[12, 30], [16, 0], [19, 30]]) {
    const target = hour * 60 + minute;
    const now = h * 60 + m;
    if (now >= target && now < target + 30) {
      return String(hour).padStart(2, "0") + ":" + String(minute).padStart(2, "0");
    }
  }
  return null;
}

function collectionWindow(clock) {
  const [h, m] = clock.split(":").map(Number);
  const now = h * 60 + m;
  return (
    (now >= 9 * 60 && now <= 12 * 60 + 20) ||
    (now >= 12 * 60 + 31 && now <= 15 * 60 + 50) ||
    (now >= 16 * 60 + 1 && now <= 19 * 60 + 20)
  );
}

const ROME_CLOCK = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Rome",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function italianTime(timestamp) {
  const parts = ROME_CLOCK.formatToParts(new Date(timestamp));
  const hour = parts.find((p) => p.type === "hour")?.value;
  const minute = parts.find((p) => p.type === "minute")?.value;
  return hour + ":" + minute;
}

async function dispatchWorkflow(env, workflow) {
  const repo = env.GITHUB_REPO || "zazoomtek-coder/zazoomtek-site";
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
    throw new Error("GitHub workflow dispatch failed (" + workflow + "): HTTP " +
      response.status + " " + (await response.text()).slice(0, 250));
  }
}

export default {
  async scheduled(event, env) {
    const localTime = italianTime(event.scheduledTime);
    const slot = activeSlot(localTime);
    const collect = collectionWindow(localTime);

    if (!slot && !collect) {
      console.log("Outside Italian editorial windows", localTime);
      return;
    }
    if (!env.GITHUB_TOKEN) throw new Error("Missing GITHUB_TOKEN secret");

    // Importing is independent from publishing: this workflow only writes to
    // editorial-queue and cannot deploy the public website.
    if (collect) {
      await dispatchWorkflow(env, "editorial-collect.yml");
      console.log("YouTube collection dispatched", localTime, "Europe/Rome");
    }

    // A release is requested only at 12:30, 16:00 or 19:30 local time.
    // Repeated five-minute attempts provide recovery if GitHub is temporarily
    // unavailable; the release receipt prevents duplicate publication.
    if (slot) {
      await dispatchWorkflow(env, env.GITHUB_WORKFLOW || "editorial-publish.yml");
      console.log("Editorial publication dispatched", slot, "Europe/Rome");
    }
  },
};
