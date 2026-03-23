import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AssessmentProvider } from './context/AssessmentContext';
import { DashboardProvider } from './context/DashboardContext';
import { AdminProvider } from './context/AdminContext';
import { PrivateRoute } from './components/PrivateRoute';
import { AdminLayout } from './components/AdminLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { AssessmentWizard } from './pages/AssessmentWizard';
import { AssessmentResults } from './pages/AssessmentResults';
import { AdminDashboard } from './pages/AdminDashboard';
import { MembersManagement } from './pages/MembersManagement';
import { InvitesManagement } from './pages/InvitesManagement';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          
          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <DashboardProvider>
                  <Dashboard />
                </DashboardProvider>
              </PrivateRoute>
            }
          />
          
          <Route
            path="/assessment"
            element={
              <PrivateRoute>
                <AssessmentProvider>
                  <AssessmentWizard />
                </AssessmentProvider>
              </PrivateRoute>
            }
          />
          
          <Route
            path="/assessment-results"
            element={
              <PrivateRoute>
                <AssessmentProvider>
                  <AssessmentResults />
                </AssessmentProvider>
              </PrivateRoute>
            }
          />
          
          {/* Admin Routes */}
          <Route
            path="/admin"
            element={
              <PrivateRoute>
                <AdminProvider>
                  <AdminLayout>
                    <AdminDashboard />
                  </AdminLayout>
                </AdminProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/admin/members"
            element={
              <PrivateRoute>
                <AdminProvider>
                  <AdminLayout>
                    <MembersManagement />
                  </AdminLayout>
                </AdminProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/admin/invites"
            element={
              <PrivateRoute>
                <AdminProvider>
                  <AdminLayout>
                    <InvitesManagement />
                  </AdminLayout>
                </AdminProvider>
              </PrivateRoute>
            }
          />
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
