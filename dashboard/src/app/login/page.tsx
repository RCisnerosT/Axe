import { login } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; error?: string }>;
}) {
  const { from, error } = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <form action={login} className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-card p-6">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold text-foreground">Axe Scanner</h1>
          <p className="text-sm text-muted-foreground">Enter the dashboard password to continue.</p>
        </div>
        <input type="hidden" name="from" value={from ?? "/"} />
        <input
          type="password"
          name="password"
          autoFocus
          placeholder="Password"
          className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
        />
        {error && <p className="text-sm text-destructive">Incorrect password.</p>}
        <button
          type="submit"
          className="w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Sign in
        </button>
      </form>
    </div>
  );
}
