// web/src/pages/ClientManager.tsx
// Phase 5 — Multi-client workspace management page.

import { useState, useEffect } from 'react';
import { clientsApi } from '../api/clients';
import { useClientStore } from '../store/clientStore';
import type { ClientRecord } from '../types';

import ClientTable from '../components/clients/ClientTable';
import ClientDetailPanel from '../components/clients/ClientDetailPanel';
import NewClientModal from '../components/clients/NewClientModal';
import TopBar from '../components/layout/TopBar';

const _styles = `
.cm-page {
  max-width: 900px;
  padding: 24px 28px;
}
.cm-new-btn {
  padding: 7px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.cm-new-btn:hover {
  background: var(--accent-hover);
}
.cm-error {
  padding: 12px 16px;
  background: var(--danger-light);
  border-radius: 8px;
  color: var(--danger);
  font-size: 13px;
  margin-bottom: 20px;
}
`;

if (typeof document !== 'undefined') {
  const id = 'cm-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

export default function ClientManager() {
  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [activeClient, setActiveClientLocal] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Update the sidebar active-client label immediately on switch
  const { setActiveClient } = useClientStore();

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [list, active] = await Promise.all([
        clientsApi.list(),
        clientsApi.active(),
      ]);
      setClients(list);
      setActiveClientLocal(active.name);
      // Auto-select the active client on first load only
      if (!selectedName) setSelectedName(active.name);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load clients.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleSwitch(name: string) {
    try {
      await clientsApi.switchTo(name);
      setActiveClient(name);      // update Zustand so sidebar reflects change instantly
      await load();
    } catch (err: any) {
      setError(err?.message ?? 'Failed to switch client.');
    }
  }

  return (
    <div className="cm-page">
      <TopBar
        title="Client Manager"
        actions={
          <button
            className="cm-new-btn"
            onClick={() => setShowNewModal(true)}
          >
            + New Client
          </button>
        }
      />

      {error && <div className="cm-error">✗ {error}</div>}

      <ClientTable
        clients={clients}
        selectedName={selectedName}
        onSelect={setSelectedName}
        onSwitch={handleSwitch}
        loading={loading}
      />

      {selectedName && (
        <ClientDetailPanel
          name={selectedName}
          isActive={selectedName === activeClient}
          onSwitch={handleSwitch}
          onDeleted={() => {
            setSelectedName(null);
            load();
          }}
          onUpdated={load}
        />
      )}

      <NewClientModal
        isOpen={showNewModal}
        onCancel={() => setShowNewModal(false)}
        onCreated={(name) => {
          setShowNewModal(false);
          load();
          setSelectedName(name);
        }}
      />
    </div>
  );
}
