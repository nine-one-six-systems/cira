/**
 * React Router configuration
 */

import { createBrowserRouter } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/Layout';
import PageLoader from './components/PageLoader';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const AddCompany = lazy(() => import('./pages/AddCompany'));
const BatchUpload = lazy(() => import('./pages/BatchUpload'));
const CompanyProgress = lazy(() => import('./pages/CompanyProgress'));
const CompanyResults = lazy(() => import('./pages/CompanyResults'));
const Settings = lazy(() => import('./pages/Settings'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Wrap lazy components with Suspense
function withSuspense(Component: React.LazyExoticComponent<React.ComponentType<unknown>>) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: withSuspense(Dashboard),
      },
      {
        path: 'add',
        element: withSuspense(AddCompany),
      },
      {
        path: 'batch',
        element: withSuspense(BatchUpload),
      },
      {
        path: 'companies/:id/progress',
        element: withSuspense(CompanyProgress),
      },
      {
        path: 'companies/:id',
        element: withSuspense(CompanyResults),
      },
      {
        path: 'settings',
        element: withSuspense(Settings),
      },
      {
        path: '*',
        element: withSuspense(NotFound),
      },
    ],
  },
]);
