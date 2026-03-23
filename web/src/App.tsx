import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'

function Home() {
  return (
    <div className="home">
      <h1>GPS Assessment Platform</h1>
      <p>Welcome to the Gift, Passion, Story assessment platform.</p>
      <div className="status-card">
        <h2>Phase 0 Status: In Progress</h2>
        <ul>
          <li>✅ Project structure created</li>
          <li>✅ FastAPI backend initialized</li>
          <li>✅ React frontend initialized</li>
          <li>⏳ Environment configuration</li>
          <li>⏳ Deploy to Render</li>
        </ul>
      </div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </Router>
  )
}

export default App
