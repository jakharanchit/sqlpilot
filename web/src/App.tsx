// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar }        from "@/components/layout/Sidebar";
import Dashboard          from "@/pages/Dashboard";
import Optimizer          from "@/pages/Optimizer";
import PlanVisualizer     from "@/pages/PlanVisualizer";
import DeploymentGate     from "@/pages/DeploymentGate";
import History            from "@/pages/History";
import ModelManager       from "@/pages/ModelManager";
import ClientManager      from "@/pages/ClientManager";
import Settings           from "@/pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
          <Routes>
            <Route path="/"            element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"   element={<Dashboard />} />
            <Route path="/optimizer"   element={<Optimizer />} />
            <Route path="/visualizer"  element={<PlanVisualizer />} />
            <Route path="/deploy"      element={<DeploymentGate />} />
            <Route path="/history"     element={<History />} />
            <Route path="/models"      element={<ModelManager />} />
            <Route path="/clients"     element={<ClientManager />} />
            <Route path="/settings"    element={<Settings />} />
            <Route path="*"            element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
