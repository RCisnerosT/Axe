import Link from "next/link";
import { logout } from "@/app/login/actions";

export function Nav() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-sm font-semibold text-foreground">
          Axe Scanner
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            Divergences
          </Link>
          <Link href="/backtest" className="text-muted-foreground hover:text-foreground">
            Backtest
          </Link>
          <form action={logout}>
            <button type="submit" className="text-muted-foreground hover:text-foreground">
              Sign out
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
