import Link from "next/link";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/compounds", label: "Compound Explorer" },
  { href: "/safety", label: "Safety Phenotype" },
  { href: "/molecular-vs-safety", label: "Molecular vs. Safety" },
  { href: "/clustering", label: "Clustering" },
  { href: "/misuse", label: "Therapeutic vs. Misuse" },
  { href: "/methods", label: "Methods" },
  { href: "/limitations", label: "Limitations" },
];

export function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-3">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <Link href="/" className="font-semibold text-slate-900 whitespace-nowrap">
            Structure-to-Safety
          </Link>
          <nav className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-slate-600 hover:text-slate-900 hover:underline whitespace-nowrap"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
