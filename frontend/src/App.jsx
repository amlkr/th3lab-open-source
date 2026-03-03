import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Sidebar from './components/Sidebar'

import LandingPage        from './pages/LandingPage'
import LoginPage          from './pages/LoginPage'
import RegisterPage       from './pages/RegisterPage'
import DashboardPage      from './pages/DashboardPage'
import ProjectsPage       from './pages/ProjectsPage'
import ProjectDetailPage  from './pages/ProjectDetailPage'
import LorasPage          from './pages/LorasPage'
import GalleryPage        from './pages/GalleryPage'
import StudioPage         from './pages/StudioPage'
import MultimediaPage     from './pages/MultimediaPage'
import ReportsPage        from './pages/ReportsPage'

import './App.css'

function Layout({ children }) {
  return (
    <div className="app">
      <Sidebar />
      <div className="app-content">{children}</div>
    </div>
  )
}

function Protected({ children }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/"          element={<LandingPage />} />
          <Route path="/login"     element={<LoginPage />} />
          <Route path="/register"  element={<RegisterPage />} />

          {/* Protected */}
          <Route path="/dashboard"     element={<Protected><DashboardPage /></Protected>} />
          <Route path="/projects"      element={<Protected><ProjectsPage /></Protected>} />
          <Route path="/projects/:id"  element={<Protected><ProjectDetailPage /></Protected>} />
          <Route path="/studio/:id?"   element={<Protected><StudioPage /></Protected>} />
          <Route path="/loras"         element={<Protected><LorasPage /></Protected>} />
          <Route path="/gallery"       element={<Protected><GalleryPage /></Protected>} />
          <Route path="/multimedia"    element={<Protected><MultimediaPage /></Protected>} />
          <Route path="/reports"       element={<Protected><ReportsPage /></Protected>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
