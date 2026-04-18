import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';

export type Organization = components['schemas']['OrganizationPublic'];
export type OrganizationUpdate = components['schemas']['OrganizationUpdate'];
export type OrganizationCreate = components['schemas']['OrganizationCreate'];
export type MembershipRole = Organization['role'];

// Centralized role gates; keep this aligned with the spec in
// `Requirements.md` so UI checks never drift from the backend.
const EDITOR_ROLES: readonly MembershipRole[] = ['owner', 'editor'] as const;
const GRADER_ROLES: readonly MembershipRole[] = ['owner', 'editor', 'grader'] as const;

export const useOrgsStore = defineStore('orgs', () => {
  const items = ref<Organization[]>([]);
  const bySlug = ref<Record<string, Organization>>({});
  const listLoaded = ref(false);
  const loading = ref(false);

  const list = computed<Organization[]>(() => items.value);

  function cache(org: Organization): void {
    bySlug.value[org.slug] = org;
    const idx = items.value.findIndex((o) => o.id === org.id);
    if (idx >= 0) {
      items.value.splice(idx, 1, org);
    } else {
      items.value.push(org);
    }
  }

  async function fetchAll(): Promise<Organization[]> {
    loading.value = true;
    try {
      const { data, error } = await getApiClient().GET('/api/v1/orgs');
      if (error) {
        return items.value;
      }
      items.value = data ?? [];
      bySlug.value = Object.fromEntries(items.value.map((o) => [o.slug, o]));
      listLoaded.value = true;
      return items.value;
    } finally {
      loading.value = false;
    }
  }

  async function fetchOne(slug: string): Promise<Organization | null> {
    const { data, error } = await getApiClient().GET('/api/v1/orgs/{org_slug}', {
      params: { path: { org_slug: slug } },
    });
    if (error || !data) {
      return null;
    }
    cache(data);
    return data;
  }

  async function create(body: OrganizationCreate): Promise<Organization | null> {
    const { data, error } = await getApiClient().POST('/api/v1/orgs', { body });
    if (error || !data) {
      return null;
    }
    cache(data);
    return data;
  }

  async function update(slug: string, body: OrganizationUpdate): Promise<Organization | null> {
    const { data, error } = await getApiClient().PATCH('/api/v1/orgs/{org_slug}', {
      params: { path: { org_slug: slug } },
      body,
    });
    if (error || !data) {
      return null;
    }
    // If the slug changed, replace the cached entry.
    if (data.slug !== slug && bySlug.value[slug]) {
      delete bySlug.value[slug];
    }
    cache(data);
    return data;
  }

  function get(slug: string): Organization | undefined {
    return bySlug.value[slug];
  }

  function roleOf(slug: string): MembershipRole | null {
    return bySlug.value[slug]?.role ?? null;
  }

  function isOwner(slug: string): boolean {
    return roleOf(slug) === 'owner';
  }

  function canEdit(slug: string): boolean {
    const role = roleOf(slug);
    return role !== null && EDITOR_ROLES.includes(role);
  }

  function canGrade(slug: string): boolean {
    const role = roleOf(slug);
    return role !== null && GRADER_ROLES.includes(role);
  }

  return {
    items,
    list,
    loading,
    listLoaded,
    fetchAll,
    fetchOne,
    create,
    update,
    get,
    roleOf,
    isOwner,
    canEdit,
    canGrade,
  };
});
