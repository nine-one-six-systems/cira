/**
 * Company Results Page - Analysis results display
 */

import { Link, useParams } from 'react-router-dom';

export default function CompanyResults() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-neutral-500 hover:text-neutral-700">
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold text-neutral-900">Company Results</h1>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50">
            Export
          </button>
          <button className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-700">
            Re-scan
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200">
        <nav className="flex gap-8">
          <button className="py-4 px-1 border-b-2 border-primary font-medium text-primary">
            Summary
          </button>
          <button className="py-4 px-1 border-b-2 border-transparent text-neutral-500 hover:text-neutral-700">
            Entities
          </button>
          <button className="py-4 px-1 border-b-2 border-transparent text-neutral-500 hover:text-neutral-700">
            Pages
          </button>
          <button className="py-4 px-1 border-b-2 border-transparent text-neutral-500 hover:text-neutral-700">
            Token Usage
          </button>
        </nav>
      </div>

      {/* Content placeholder */}
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-neutral-500">
          Loading results for company {id}...
        </p>
      </div>
    </div>
  );
}
