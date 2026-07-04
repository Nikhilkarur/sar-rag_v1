import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { AppLayout } from '../components/layout/AppLayout'
import AuthLayout from '../layouts/AuthLayout'
import Landing from '../pages/Landing/Landing'
import { Login } from '../pages/auth/Login'
import { Signup } from '../pages/auth/Signup'
import { StatusPage } from '../pages/portal/StatusPage'
import { Queue } from '../pages/portal/Queue'
import { SARWorkspace } from '../pages/portal/SARWorkspace'
import { Usage } from '../pages/portal/Usage'
import { Credentials } from '../pages/portal/settings/Credentials'
import { Webhook } from '../pages/portal/settings/Webhook'
import { Schema } from '../pages/portal/settings/Schema'
import { LLMConfig } from '../pages/portal/settings/LLMConfig'
import { Billing } from '../pages/portal/settings/Billing'
import { Overview } from '../pages/admin/Overview'
import { Verifications } from '../pages/admin/Verifications'
import { Customers } from '../pages/admin/Customers'
import { Logs } from '../pages/admin/Logs'
import { GroqUsage } from '../pages/admin/GroqUsage'
import { Billing as AdminBilling } from '../pages/admin/Billing'

/** Tenant portal guard: must be authed, not a super admin, and ACTIVE. */
function PortalGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  if (user.role === 'SUPER_ADMIN') return <Navigate to="/admin/overview" replace />
  if (user.tenant && user.tenant.status !== 'ACTIVE') return <Navigate to="/status" replace />
  return <>{children}</>
}

/** Admin guard: must be authed with SUPER_ADMIN role. */
function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  if (user.role !== 'SUPER_ADMIN') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

/** Public-only guard: bounce signed-in users to their home. */
function PublicOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore()
  if (isAuthenticated && user) {
    if (user.role === 'SUPER_ADMIN') return <Navigate to="/admin/overview" replace />
    if (user.tenant && user.tenant.status !== 'ACTIVE') return <Navigate to="/status" replace />
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}

function StatusRoute() {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  if (user.tenant?.status === 'ACTIVE') return <Navigate to="/dashboard" replace />
  return <StatusPage />
}

export function AppRouter() {
  return (
    <Routes>
      {/* Public landing — fully standalone */}
      <Route path="/" element={<Landing />} />

      {/* Auth pages — universe behind frosted glass */}
      <Route element={<AuthLayout />}>
        <Route
          path="/login"
          element={
            <PublicOnly>
              <Login />
            </PublicOnly>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicOnly>
              <Signup />
            </PublicOnly>
          }
        />
        <Route path="/status" element={<StatusRoute />} />
      </Route>

      {/* Client portal */}
      <Route
        element={
          <PortalGuard>
            <AppLayout />
          </PortalGuard>
        }
      >
        {/* Dashboard and Usage merged into one central dashboard (the Usage view). */}
        <Route path="/dashboard" element={<Usage />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/queue/:alertId" element={<SARWorkspace />} />
        <Route path="/usage" element={<Navigate to="/dashboard" replace />} />
        <Route path="/settings/credentials" element={<Credentials />} />
        <Route path="/settings/webhook" element={<Webhook />} />
        <Route path="/settings/schema" element={<Schema />} />
        <Route path="/settings/llm" element={<LLMConfig />} />
        <Route path="/settings/billing" element={<Billing />} />
      </Route>

      {/* Admin console */}
      <Route
        element={
          <AdminGuard>
            <AppLayout admin />
          </AdminGuard>
        }
      >
        <Route path="/admin/overview" element={<Overview />} />
        <Route path="/admin/verifications" element={<Verifications />} />
        <Route path="/admin/customers" element={<Customers />} />
        <Route path="/admin/logs" element={<Logs />} />
        <Route path="/admin/billing" element={<AdminBilling />} />
        <Route path="/admin/llm" element={<GroqUsage />} />
        {/* legacy path — keep old bookmarks working */}
        <Route path="/admin/groq" element={<Navigate to="/admin/llm" replace />} />
      </Route>
      <Route path="/admin" element={<Navigate to="/admin/overview" replace />} />

      {/* Unknown routes fall back to the landing page */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
