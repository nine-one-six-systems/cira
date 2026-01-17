/**
 * Add Company Page - Single company input form
 */

import { Link } from 'react-router-dom';

export default function AddCompany() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/" className="text-neutral-500 hover:text-neutral-700">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold text-neutral-900">Add Company</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <form className="space-y-4">
          <div>
            <label htmlFor="companyName" className="block text-sm font-medium text-neutral-700 mb-1">
              Company Name *
            </label>
            <input
              type="text"
              id="companyName"
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="Acme Corp"
            />
          </div>

          <div>
            <label htmlFor="websiteUrl" className="block text-sm font-medium text-neutral-700 mb-1">
              Website URL *
            </label>
            <input
              type="url"
              id="websiteUrl"
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="https://www.example.com"
            />
          </div>

          <div>
            <label htmlFor="industry" className="block text-sm font-medium text-neutral-700 mb-1">
              Industry
            </label>
            <input
              type="text"
              id="industry"
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary focus:border-primary"
              placeholder="Technology"
            />
          </div>

          <button
            type="submit"
            className="w-full px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-700"
          >
            Start Analysis
          </button>
        </form>
      </div>
    </div>
  );
}
