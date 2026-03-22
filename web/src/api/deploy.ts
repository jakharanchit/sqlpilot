// web/src/api/deploy.ts
import { apiFetch } from './client';
import type { DeployPreview, DeployPackage } from '../types';

export const deployApi = {
  /** Build deploy.sql + rollback.sql in memory — does NOT write to disk. */
  preview: (): Promise<DeployPreview> =>
    apiFetch<DeployPreview>('/api/deploy/preview'),

  /** Call generate_deployment_package() — writes files to disk. */
  generate: (opts?: {
    client?:      string;
    include_all?: boolean;
  }): Promise<DeployPackage> =>
    apiFetch<DeployPackage>('/api/deploy/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(opts ?? {}),
    }),

  /** List all previously generated packages. */
  listPackages: (): Promise<DeployPackage[]> =>
    apiFetch<DeployPackage[]>('/api/deploy/packages'),

  /** Fetch raw plain-text content of a file inside a package. */
  getFile: (folderName: string, filename: string): Promise<string> =>
    fetch(`/api/deploy/packages/${encodeURIComponent(folderName)}/files/${encodeURIComponent(filename)}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      }),
};
