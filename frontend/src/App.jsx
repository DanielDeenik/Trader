import { BrowserRouter, Routes, Route } from 'react-router-dom'
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
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout title="Overview"><Overview /></Layout>} />
        <Route path="/tickers" element={<Layout title="Tickers"><Tickers /></Layout>} />
        <Route path="/tickers/:symbol" element={<Layout title="Ticker Detail"><TickerDetail /></Layout>} />
        <Route path="/signals" element={<Layout title="L1: Signal Radar"><SignalRadar /></Layout>} />
        <Route path="/mosaics" element={<Layout title="L2: Mosaic Cards"><MosaicCards /></Layout>} />
        <Route path="/theses" element={<Layout title="L3: Thesis Forge"><ThesisForge /></Layout>} />
        <Route path="/gate/review" element={<Layout title="HITL Gate Review"><GateReview /></Layout>} />
        <Route path="/decisions" element={<Layout title="L4: Decisions"><Decisions /></Layout>} />
        <Route path="/positions" element={<Layout title="L5: Portfolio"><Positions /></Layout>} />
        <Route path="/tasks" element={<Layout title="Task Queue"><TaskQueue /></Layout>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
