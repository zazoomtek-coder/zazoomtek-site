// Cloudflare Cron: poll YouTube and publish only when verified content changes.
// A running/queued GitHub workflow suppresses overlapping dispatches.
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

export default {
  async scheduled(event, env) {
    if (!env.GITHUB_TOKEN) {
      throw new Error("Missing GITHUB_TOKEN secret");
    }

    const repo = env.GITHUB_REPO || "zazoomtek-coder/zazoomtek-site";
    const workflow = env.GITHUB_WORKFLOW || "editorial-publish.yml";

    if (await hasActiveRun(env, repo, workflow)) {
      console.log("Skipped five-minute poll: editorial workflow is already queued or running");
      return;
    }

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
      body: JSON.stringify({ ref: "main", inputs: { release_slot: "poll" } }),
    });

    if (response.status !== 204) {
      throw new Error(
        "GitHub workflow dispatch failed: HTTP " + response.status +
        " " + (await response.text()).slice(0, 250)
      );
    }

    console.log("Five-minute YouTube import/publish poll dispatched", {
      scheduledTime: new Date(event.scheduledTime).toISOString(),
      mode: "poll",
    });
  },
};
