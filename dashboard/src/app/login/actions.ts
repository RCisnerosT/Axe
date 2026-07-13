"use server";

import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";

export async function login(formData: FormData) {
  const password = formData.get("password");
  const from = (formData.get("from") as string) || "/";

  if (password !== process.env.DASHBOARD_PASSWORD) {
    redirect(`/login?error=1&from=${encodeURIComponent(from)}`);
  }

  const session = await getSession();
  session.authenticated = true;
  await session.save();

  redirect(from);
}

export async function logout() {
  const session = await getSession();
  session.destroy();
  redirect("/login");
}
