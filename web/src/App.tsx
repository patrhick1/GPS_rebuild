import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AssessmentProvider } from './context/AssessmentContext';
import { DashboardProvider } from './context/DashboardContext';
import { AdminProvider } from './context/AdminContext';
import { MasterProvider } from './context/MasterContext';
import { BillingProvider } from './context/BillingContext';
import { PrivateRoute } from './components/PrivateRoute';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { Dashboard } from './pages/Dashboard';
import { AssessmentWizard } from './pages/AssessmentWizard';
import { AssessmentResults } from './pages/AssessmentResults';
import { MyImpactWizard } from './pages/MyImpactWizard';
import { MyImpactResults } from './pages/MyImpactResults';
import { Account } from './pages/Account';
import { Upgrade } from './pages/Upgrade';
import { ChurchRegister } from './pages/ChurchRegister';
import { ChurchUpgrade } from './pages/ChurchUpgrade';
import { AdminDashboard } from './pages/AdminDashboard';

import { MasterDashboard } from './pages/MasterDashboard';
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
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/upgrade" element={<Upgrade />} />
          <Route path="/register/church" element={<ChurchRegister />} />
          <Route
            path="/upgrade/church"
            element={
              <PrivateRoute>
                <ChurchUpgrade />
              </PrivateRoute>
            }
          />

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
          
          {/* MyImpact Routes */}
          <Route
            path="/myimpact"
            element={
              <PrivateRoute>
                <AssessmentProvider>
                  <MyImpactWizard />
                </AssessmentProvider>
              </PrivateRoute>
            }
          />
          
          <Route
            path="/myimpact-results"
            element={
              <PrivateRoute>
                <AssessmentProvider>
                  <MyImpactResults />
                </AssessmentProvider>
              </PrivateRoute>
            }
          />

          <Route
            path="/account"
            element={
              <PrivateRoute>
                <DashboardProvider>
                  <Account />
                </DashboardProvider>
              </PrivateRoute>
            }
          />

          {/* Admin Routes */}
          <Route
            path="/admin"
            element={
              <PrivateRoute requiredRole="admin_or_master">
                <AdminProvider>
                  <AdminDashboard />
                </AdminProvider>
              </PrivateRoute>
            }
          />

          {/* Master Admin Routes */}
          <Route
            path="/master"
            element={
              <PrivateRoute requiredRole="master">
                <MasterProvider>
                  <MasterDashboard />
                </MasterProvider>
              </PrivateRoute>
            }
          />

          {/* Billing Route */}
          <Route
            path="/admin/billing"
            element={
              <PrivateRoute requiredRole="admin_or_master">
                <BillingProvider>
                  <BillingDashboard />
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
