/**
 * Main application layout with header
 */

import { Link, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Skip link for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <span className="text-xl font-bold text-primary">CIRA</span>
              <span className="text-sm text-neutral-500 hidden sm:inline">
                Company Intelligence Research Assistant
              </span>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-4">
              <Link
                to="/"
                className="text-neutral-600 hover:text-neutral-900 px-3 py-2"
              >
                Dashboard
              </Link>
              <Link
                to="/settings"
                className="text-neutral-600 hover:text-neutral-900 px-3 py-2"
              >
                Settings
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main id="main-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-neutral-500 text-center">
            CIRA v1.0.0 - Company Intelligence Research Assistant
          </p>
        </div>
      </footer>
    </div>
  );
}
