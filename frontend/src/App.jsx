import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import Overview from './pages/Overview'
import Tickers from './pages/Tickers'
import TickerDetail from './pages/TickerDetail'
import SignalRadar from './pages/SignalRadar'
import MosaicCards from './pages/MosaicCards'
import ThesisForge from './pages/ThesisForge'
import GateReview from './pages/GateReview'
import Decisions from './pages/Decisions'
import Positions from './pages/Positions'
import TaskQueue from './pages/TaskQueue'
import DeepDive from './pages/DeepDive'
import LatticeGraph from './pages/LatticeGraph'
import MosaicWorkbench from './pages/MosaicWorkbench'
import Settings from './pages/Settings'
import Login from './pages/Login'
import NotFound from './pages/NotFound'

// Fiscal.ai-style workflow UI (FE-002). Public routes for demo.
import { FiscalIndex } from './views/fiscal/FiscalIndex'
import { FiscalWorkflow } from './views/fiscal/FiscalWorkflow'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-gray-400">Loading...</div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Fiscal.ai-style workflow UI — FE-002. Unauthenticated for demo. */}
      <Route path="/fiscal" element={<FiscalIndex />} />
      <Route path="/fiscal/pipeline" element={<FiscalWorkflow />} />

      <Route path="/" element={<ProtectedRoute><Layout title="Overview"><Overview /></Layout></ProtectedRoute>} />
      <Route path="/tickers" element={<ProtectedRoute><Layout title="Tickers"><Tickers /></Layout></ProtectedRoute>} />
      <Route path="/tickers/:symbol" element={<ProtectedRoute><Layout title="Ticker Detail"><TickerDetail /></Layout></ProtectedRoute>} />
      <Route path="/deepdive/:symbol" element={<ProtectedRoute><Layout title="Deep Dive"><DeepDive /></Layout></ProtectedRoute>} />
      <Route path="/lattice/:symbol" element={<ProtectedRoute><Layout title="Lattice Network"><LatticeGraph /></Layout></ProtectedRoute>} />
      <Route path="/mosaic/:symbol" element={<ProtectedRoute><Layout title="Mosaic Workbench"><MosaicWorkbench /></Layout></ProtectedRoute>} />
      <Route path="/signals" element={<ProtectedRoute><Layout title="L1: Signal Radar"><SignalRadar /></Layout></ProtectedRoute>} />
      <Route path="/mosaics" element={<ProtectedRoute><Layout title="L2: Mosaic Cards"><MosaicCards /></Layout></ProtectedRoute>} />
      <Route path="/theses" element={<ProtectedRoute><Layout title="L3: Thesis Forge"><ThesisForge /></Layout></ProtectedRoute>} />
      <Route path="/gate/review" element={<ProtectedRoute><Layout title="HITL Gate Review"><GateReview /></Layout></ProtectedRoute>} />
      <Route path="/decisions" element={<ProtectedRoute><Layout title="L4: Decisions"><Decisions /></Layout></ProtectedRoute>} />
      <Route path="/positions" element={<ProtectedRoute><Layout title="L5: Portfolio"><Positions /></Layout></ProtectedRoute>} />
      <Route path="/tasks" element={<ProtectedRoute><Layout title="Task Queue"><TaskQueue /></Layout></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Layout title="Settings"><Settings /></Layout></ProtectedRoute>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
