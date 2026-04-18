import { defineStore } from 'pinia';
import { ref } from 'vue';

import { getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';

export type SystemAnnouncement = components['schemas']['SystemAnnouncementPublic'];
export type OrgAlert = components['schemas']['OrgAlertPublic'];

/**
 * Stores two orthogonal lists:
 * - `system` — active announcements awaiting the current user's ack.
 * - `orgActive[slug]` — active alerts for each org the user has opened.
 *
 * Both are "presentation" state; the backend is the source of truth and
 * only returns rows the user has NOT dismissed.
 */
export const useAlertsStore = defineStore('alerts', () => {
  const system = ref<SystemAnnouncement[]>([]);
  const systemLoaded = ref(false);
  const orgActive = ref<Record<string, OrgAlert[]>>({});

  async function refreshSystemActive(): Promise<void> {
    const { data, error } = await getApiClient().GET('/api/v1/announcements/active', {});
    if (error || !data) return;
    system.value = data;
    systemLoaded.value = true;
  }

  async function listAllSystem(): Promise<SystemAnnouncement[] | null> {
    const { data, error } = await getApiClient().GET('/api/v1/announcements', {});
    if (error || !data) return null;
    return data;
  }

  async function createSystem(
    payload: components['schemas']['SystemAnnouncementCreate'],
  ): Promise<SystemAnnouncement | null> {
    const { data, error } = await getApiClient().POST('/api/v1/announcements', {
      body: payload,
    });
    if (error || !data) return null;
    return data;
  }

  async function deleteSystem(announcementId: string): Promise<boolean> {
    const { error } = await getApiClient().DELETE('/api/v1/announcements/{announcement_id}', {
      params: { path: { announcement_id: announcementId } },
    });
    return !error;
  }

  async function refreshOrgActive(orgSlug: string): Promise<void> {
    const { data, error } = await getApiClient().GET('/api/v1/orgs/{org_slug}/alerts/active', {
      params: { path: { org_slug: orgSlug } },
    });
    if (error || !data) return;
    orgActive.value = { ...orgActive.value, [orgSlug]: data };
  }

  async function listAllForOrg(orgSlug: string): Promise<OrgAlert[] | null> {
    const { data, error } = await getApiClient().GET('/api/v1/orgs/{org_slug}/alerts', {
      params: { path: { org_slug: orgSlug } },
    });
    if (error || !data) return null;
    return data;
  }

  async function createForOrg(
    orgSlug: string,
    payload: components['schemas']['OrgAlertCreate'],
  ): Promise<OrgAlert | null> {
    const { data, error } = await getApiClient().POST('/api/v1/orgs/{org_slug}/alerts', {
      params: { path: { org_slug: orgSlug } },
      body: payload,
    });
    if (error || !data) return null;
    return data;
  }

  async function deleteForOrg(orgSlug: string, alertId: string): Promise<boolean> {
    const { error } = await getApiClient().DELETE('/api/v1/orgs/{org_slug}/alerts/{alert_id}', {
      params: { path: { org_slug: orgSlug, alert_id: alertId } },
    });
    return !error;
  }

  async function acknowledge(kind: 'system' | 'org', alertId: string): Promise<void> {
    const { error } = await getApiClient().POST('/api/v1/alerts/{kind}/{alert_id}/ack', {
      params: { path: { kind, alert_id: alertId } },
    });
    if (error) return;
    if (kind === 'system') {
      system.value = system.value.filter((a) => a.id !== alertId);
    } else {
      const next: Record<string, OrgAlert[]> = {};
      for (const [slug, list] of Object.entries(orgActive.value)) {
        next[slug] = list.filter((a) => a.id !== alertId);
      }
      orgActive.value = next;
    }
  }

  function reset(): void {
    system.value = [];
    systemLoaded.value = false;
    orgActive.value = {};
  }

  return {
    system,
    systemLoaded,
    orgActive,
    refreshSystemActive,
    listAllSystem,
    createSystem,
    deleteSystem,
    refreshOrgActive,
    listAllForOrg,
    createForOrg,
    deleteForOrg,
    acknowledge,
    reset,
  };
});
