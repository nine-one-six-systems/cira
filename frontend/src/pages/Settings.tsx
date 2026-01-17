/**
 * Settings Page - Configuration settings
 */

import { Link } from 'react-router-dom';

export default function Settings() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/" className="text-neutral-500 hover:text-neutral-700">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold text-neutral-900">Settings</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-4">Default Analysis Settings</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Analysis Mode
              </label>
              <select className="w-full px-3 py-2 border border-neutral-300 rounded-md">
                <option value="thorough">Thorough</option>
                <option value="quick">Quick</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Max Pages
              </label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md"
                defaultValue={100}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Max Depth
              </label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md"
                defaultValue={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Time Limit (minutes)
              </label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md"
                defaultValue={30}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button className="px-4 py-2 border border-neutral-300 rounded-md text-neutral-700 hover:bg-neutral-50">
            Reset
          </button>
          <button className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-700">
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
