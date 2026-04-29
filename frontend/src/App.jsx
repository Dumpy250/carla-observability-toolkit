import { NavLink, Route, Routes } from 'react-router-dom'
import CompareRuns from './pages/CompareRuns.jsx'
import RunExplorer from './pages/RunExplorer.jsx'

function App() {
  return (
    <div className="app-shell">
      <nav className="top-nav">
        <NavLink to="/" end className={({ isActive }) => `top-nav-link${isActive ? ' active' : ''}`}>
          Run Explorer
        </NavLink>
        <NavLink
          to="/compare"
          className={({ isActive }) => `top-nav-link${isActive ? ' active' : ''}`}
        >
          Compare Runs
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<RunExplorer />} />
        <Route path="/compare" element={<CompareRuns />} />
      </Routes>
    </div>
  )
}

export default App
