import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AssessmentProvider } from './context/AssessmentContext';
import { DashboardProvider } from './context/DashboardContext';
import { AdminProvider } from './context/AdminContext';
import { MasterProvider } from './context/MasterContext';
import { BillingProvider } from './context/BillingContext';
import { PrivateRoute } from './components/PrivateRoute';
import { AdminLayout } from './components/AdminLayout';
import { MasterLayout } from './components/MasterLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { AssessmentWizard } from './pages/AssessmentWizard';
import { AssessmentResults } from './pages/AssessmentResults';
import { AdminDashboard } from './pages/AdminDashboard';
import { MembersManagement } from './pages/MembersManagement';
import { InvitesManagement } from './pages/InvitesManagement';
import { MasterDashboard } from './pages/MasterDashboard';
import { ChurchesManagement } from './pages/ChurchesManagement';
import { AuditLog } from './pages/AuditLog';
import { SystemExport } from './pages/SystemExport';
import { BillingDashboard } from './pages/BillingDashboard';
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
          
          {/* Master Admin Routes */}
          <Route
            path="/master"
            element={
              <PrivateRoute>
                <MasterProvider>
                  <MasterLayout>
                    <MasterDashboard />
                  </MasterLayout>
                </MasterProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/master/churches"
            element={
              <PrivateRoute>
                <MasterProvider>
                  <MasterLayout>
                    <ChurchesManagement />
                  </MasterLayout>
                </MasterProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/master/users"
            element={
              <PrivateRoute>
                <MasterProvider>
                  <MasterLayout>
                    <div>Users Management (Coming Soon)</div>
                  </MasterLayout>
                </MasterProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/master/audit"
            element={
              <PrivateRoute>
                <MasterProvider>
                  <MasterLayout>
                    <AuditLog />
                  </MasterLayout>
                </MasterProvider>
              </PrivateRoute>
            }
          />
          <Route
            path="/master/export"
            element={
              <PrivateRoute>
                <MasterProvider>
                  <MasterLayout>
                    <SystemExport />
                  </MasterLayout>
                </MasterProvider>
              </PrivateRoute>
            }
          />
          
          {/* Billing Route */}
          <Route
            path="/admin/billing"
            element={
              <PrivateRoute>
                <BillingProvider>
                  <AdminLayout>
                    <BillingDashboard />
                  </AdminLayout>
                </BillingProvider>
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
