/**
 * Dashboard Page - Main company list view
 */

import { Link } from 'react-router-dom';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-neutral-900">Companies</h1>
        <div className="flex gap-3">
          <Link
            to="/batch"
            className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50"
          >
            Batch Upload
          </Link>
          <Link
            to="/add"
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-700"
          >
            Add Company
          </Link>
        </div>
      </div>

      {/* Placeholder for company list */}
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-neutral-500 text-center">
          No companies yet. Add a company to get started.
        </p>
      </div>
    </div>
  );
}
