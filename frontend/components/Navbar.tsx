import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-4">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-600">
            <span className="text-sm font-bold text-white">E</span>
          </div>

          <span className="text-xl font-bold text-gray-800">
            ESG <span className="text-green-600">Platform</span>
          </span>
        </div>

        {/* Menu */}
        <div className="flex items-center gap-8 text-sm font-medium text-gray-600">
          <Link href="/" className="transition hover:text-green-600">
            Home
          </Link>

          <Link href="/upload" className="transition hover:text-green-600">
            Upload
          </Link>

          <Link href="/dashboard" className="transition hover:text-green-600">
            Dashboard
          </Link>
        </div>

      </div>
    </nav>
  );
}