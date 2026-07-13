import { NextResponse, type NextRequest } from "next/server";

const REPO_OWNER = "RCisnerosT";
const REPO_NAME = "Axe";
const WORKFLOW_FILE = "scan.yml";

// Hit by cron-job.org every ~15 min during market hours -- more reliable
// timing than GitHub's own `schedule` trigger, which can lag 5-30 min.
// Protected by a shared secret (not real auth) since this only ever
// triggers a public repo's own scan workflow; the GitHub PAT that does
// the actual work lives server-side, never exposed to the caller.
export async function POST(request: NextRequest) {
  const secret = request.nextUrl.searchParams.get("secret");
  if (!secret || secret !== process.env.TRIGGER_SECRET) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const githubPat = process.env.GITHUB_PAT;
  if (!githubPat) {
    return NextResponse.json({ error: "GITHUB_PAT not configured" }, { status: 500 });
  }

  const response = await fetch(
    `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${githubPat}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );

  if (!response.ok) {
    const body = await response.text();
    return NextResponse.json({ error: "github dispatch failed", status: response.status, body }, { status: 502 });
  }

  return NextResponse.json({ status: "ok" });
}

export async function GET(request: NextRequest) {
  return POST(request);
}
