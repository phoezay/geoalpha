import { createBrowserRouter } from 'react-router'
import { AppShell } from './AppShell'
import { HistoryPage } from './HistoryPage'
import { NewRunPage } from './NewRunPage'
import { NotFound } from './NotFoundPage'
import { RunReportPage } from './RunReportPage'

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <NewRunPage /> },
      { path: '/runs/:id', element: <RunReportPage /> },
      { path: '/history', element: <HistoryPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])
