import { createClient } from "@supabase/supabase-js";

// Server-only client using the service_role key -- this file must never be
// imported from a "use client" component. The dashboard is a single-user
// tool behind password auth (see middleware.ts), so reading with the
// privileged key server-side (never sent to the browser) is simpler than
// standing up RLS policies for a reader that doesn't exist yet.
export function getSupabaseClient() {
  let url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set");
  }
  // createClient appends the REST path itself — strip it in case the
  // project's base URL was copied from the "Data API" endpoint instead of
  // the plain Project URL (e.g. "https://xxx.supabase.co/rest/v1/").
  url = url.replace(/\/+$/, "");
  if (url.endsWith("/rest/v1")) {
    url = url.slice(0, -"/rest/v1".length);
  }
  return createClient(url, key, { auth: { persistSession: false } });
}
