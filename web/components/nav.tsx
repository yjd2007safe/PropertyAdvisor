import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/suburbs", label: "Suburb Dashboard" },
  { href: "/advisor", label: "Property Advisor" },
  { href: "/comparables", label: "Comparables" },
  { href: "/watchlist", label: "Watchlist & Alerts" },
  { href: "/orchestration", label: "Orchestration Review" }
];

export function Nav() {
  return (
    <header className="topbar">
      <div>
        <p className="brand-kicker">PropertyAdvisor</p>
        <h1 className="brand-title">Unified decision-support MVP</h1>
      </div>
      <nav aria-label="Primary">
        <ul className="nav-list">
          {links.map((link) => (
            <li key={link.href}>
              <Link href={link.href}>{link.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
