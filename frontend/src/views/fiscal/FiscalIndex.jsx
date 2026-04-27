/**
 * FiscalIndex — landing page for /fiscal. Currently redirects to the
 * Workflow Pipeline view since that's the most informative starting
 * point. Future: replace with a configurable home dashboard.
 */
import { Navigate } from 'react-router-dom'
export function FiscalIndex() {
  return <Navigate to="/fiscal/pipeline" replace />
}
