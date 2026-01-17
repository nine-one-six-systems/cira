/**
 * Company Progress Page - Real-time progress monitoring
 */

import { Link, useParams } from 'react-router-dom';

export default function CompanyProgress() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/" className="text-neutral-500 hover:text-neutral-700">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold text-neutral-900">Analysis Progress</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-neutral-500">Analyzing...</span>
            <span className="font-medium">0%</span>
          </div>
          <div className="h-2 bg-neutral-200 rounded-full">
            <div className="h-full bg-primary rounded-full w-0" />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-neutral-50 rounded-lg">
            <div className="text-2xl font-bold text-neutral-900">0</div>
            <div className="text-sm text-neutral-500">Pages Crawled</div>
          </div>
          <div className="text-center p-4 bg-neutral-50 rounded-lg">
            <div className="text-2xl font-bold text-neutral-900">0</div>
            <div className="text-sm text-neutral-500">Entities Found</div>
          </div>
          <div className="text-center p-4 bg-neutral-50 rounded-lg">
            <div className="text-2xl font-bold text-neutral-900">0</div>
            <div className="text-sm text-neutral-500">Tokens Used</div>
          </div>
        </div>

        {/* Current activity */}
        <div className="text-center text-neutral-500">
          Waiting to start... (Company ID: {id})
        </div>

        {/* Actions */}
        <div className="flex justify-center gap-4">
          <button className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50">
            Pause
          </button>
          <button className="px-4 py-2 border border-error-500 rounded-md text-error-500 hover:bg-error-50">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
