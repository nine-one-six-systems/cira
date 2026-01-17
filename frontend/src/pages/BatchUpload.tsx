/**
 * Batch Upload Page - CSV batch upload interface
 */

import { Link } from 'react-router-dom';

export default function BatchUpload() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/" className="text-neutral-500 hover:text-neutral-700">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold text-neutral-900">Batch Upload</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center">
          <p className="text-neutral-500">
            Drop CSV file here or click to browse
          </p>
          <input type="file" accept=".csv" className="hidden" />
        </div>

        <div className="text-center">
          <button className="text-primary hover:underline">
            Download CSV Template
          </button>
        </div>
      </div>
    </div>
  );
}
