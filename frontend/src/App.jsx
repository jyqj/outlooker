import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import VerificationPage from './pages/VerificationPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import ToastContainer from './components/Toast';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const token = sessionStorage.getItem('admin_token');
  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }
  return children;
};

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<VerificationPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute>
              <AdminDashboardPage />
            </ProtectedRoute>
          } 
        />
      </Routes>
      <ToastContainer />
    </>
  );
}

export default App;
