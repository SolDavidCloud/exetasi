import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getApiClient } from 'src/api/client';

export interface AuthUser {
  id: string;
  username: string;
  bio: string;
  avatar_url: string | null;
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null);
  const loaded = ref(false);

  const isAuthenticated = computed(() => user.value !== null);

  async function fetchSession(): Promise<void> {
    const { data, error } = await getApiClient().GET('/api/v1/users/me');
    loaded.value = true;
    if (error) {
      user.value = null;
      return;
    }
    user.value = data ?? null;
  }

  async function devLogin(username: string): Promise<void> {
    const { error } = await getApiClient().POST('/api/v1/auth/dev/login', {
      body: { username },
    });
    if (error) {
      throw new Error('login_failed');
    }
    await fetchSession();
  }

  async function logout(): Promise<void> {
    await getApiClient().POST('/api/v1/auth/logout');
    user.value = null;
  }

  return {
    user,
    loaded,
    isAuthenticated,
    fetchSession,
    devLogin,
    logout,
  };
});
