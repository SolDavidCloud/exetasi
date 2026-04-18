<template>
  <q-page class="app-container q-py-xl">
    <div v-if="!org && !loading">
      <EmptyState
        icon="search_off"
        :title="t('orgs.notFoundTitle')"
        :description="t('orgs.notFoundDesc')"
      >
        <q-btn unelevated color="primary" :to="{ name: 'orgs' }" :label="t('orgs.backToList')" />
      </EmptyState>
    </div>

    <div v-else-if="org" :style="themeStyles">
      <OrgBanner :banner-url="org.banner_url" class="org-detail-banner">
        <div class="org-detail-banner__content app-container">
          <OrgAvatar
            :name="org.name"
            :avatar-url="org.avatar_url"
            :primary-color="org.primary_color"
            :secondary-color="org.secondary_color"
            :size="96"
            class="org-detail-banner__avatar"
          />
          <div class="org-detail-banner__text">
            <div class="org-detail-banner__chips">
              <p class="app-chip">
                {{ org.is_personal ? t('orgs.personalBadge') : t('orgs.teamBadge') }}
              </p>
              <p class="app-chip">{{ t(`orgs.roles.${org.role}`) }}</p>
            </div>
            <h1 class="org-detail-banner__title">{{ org.name }}</h1>
            <p class="org-detail-banner__slug">{{ slugUrl }}</p>
          </div>
          <div class="org-detail-banner__actions row q-gutter-sm">
            <q-btn
              v-if="!isOwner && !org.is_personal"
              outline
              color="white"
              icon="chat"
              :label="t('messages.compose.toOrgOwners')"
              @click="composeToOwnersOpen = true"
            />
            <q-btn
              v-if="isOwner"
              unelevated
              color="primary"
              icon="settings"
              :label="t('orgs.settings.open')"
              :to="{ name: 'org-settings', params: { slug: org.slug } }"
            />
          </div>
        </div>
      </OrgBanner>

      <section v-if="org.description" class="q-mt-lg app-panel">
        <p class="org-detail-section-title">{{ t('orgs.aboutTitle') }}</p>
        <p class="q-mt-sm q-mb-none">{{ org.description }}</p>
      </section>

      <section class="q-mt-lg">
        <div class="row items-center justify-between q-mb-md">
          <h2 class="org-detail-section-title">{{ t('orgs.examsTitle') }}</h2>
        </div>
        <EmptyState
          v-if="!examsLoading && exams.length === 0"
          icon="quiz"
          :title="t('orgs.examsEmptyTitle')"
          :description="t('orgs.examsEmptyDesc')"
        />
        <div v-else class="app-grid">
          <article v-for="e in exams" :key="e.id" class="app-panel exam-card">
            <q-icon name="quiz" size="24px" class="exam-card__icon" />
            <div class="exam-card__text">
              <p class="exam-card__name">{{ e.name }}</p>
              <p class="app-muted q-ma-none exam-card__meta">
                <span>{{ t(`orgs.visibility.${e.visibility}`) }}</span>
                <span v-if="e.is_archived"> · {{ t('orgs.archived') }}</span>
              </p>
            </div>
          </article>
        </div>
      </section>
    </div>

    <MessageComposeDialog
      v-if="org"
      v-model="composeToOwnersOpen"
      mode="org_owners"
      :org-slug="org.slug"
    />

    <AlertDialog
      v-if="org"
      :alerts="orgAlertsList"
      kind="org"
      @acknowledge="(id) => void alerts.acknowledge('org', id)"
    />
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import AlertDialog from 'components/AlertDialog.vue';
import EmptyState from 'components/EmptyState.vue';
import MessageComposeDialog from 'components/MessageComposeDialog.vue';
import OrgAvatar from 'components/OrgAvatar.vue';
import OrgBanner from 'components/OrgBanner.vue';
import { getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';
import { useOrgTheme } from 'src/composables/useOrgTheme';
import { useAlertsStore } from 'src/stores/alerts-store';
import { useOrgsStore, type Organization } from 'src/stores/orgs-store';

type Exam = components['schemas']['ExamPublic'];

const { t } = useI18n();
const route = useRoute();
const orgs = useOrgsStore();
const alerts = useAlertsStore();

const loading = ref(false);
const examsLoading = ref(false);
const exams = ref<Exam[]>([]);
const composeToOwnersOpen = ref(false);

const slug = computed(() => String(route.params.slug ?? ''));
const org = computed<Organization | null>(() => orgs.get(slug.value) ?? null);
const { styles: themeStyles } = useOrgTheme(org);

const slugUrl = computed(() => `/#/orgs/${slug.value}`);
const isOwner = computed(() => orgs.isOwner(slug.value));
const orgAlertsList = computed(() => alerts.orgActive[slug.value] ?? []);

async function load(): Promise<void> {
  loading.value = true;
  try {
    await orgs.fetchOne(slug.value);
  } finally {
    loading.value = false;
  }
  await Promise.all([loadExams(), alerts.refreshOrgActive(slug.value)]);
}

async function loadExams(): Promise<void> {
  examsLoading.value = true;
  try {
    const { data, error } = await getApiClient().GET('/api/v1/orgs/{org_slug}/exams', {
      params: { path: { org_slug: slug.value } },
    });
    exams.value = error ? [] : (data ?? []);
  } finally {
    examsLoading.value = false;
  }
}

onMounted(() => {
  void load();
});

watch(slug, (next, prev) => {
  if (next && next !== prev) {
    void load();
  }
});
</script>

<style scoped lang="scss">
.org-detail-banner {
  height: clamp(180px, 26vw, 280px);
}
.org-detail-banner__content {
  position: absolute;
  inset: auto 0 0 0;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: end;
  gap: 16px;
  padding-block: 20px;
  padding-inline: clamp(16px, 3vw, 28px);
  color: white;
}
.org-detail-banner__avatar {
  border: 3px solid rgba(255, 255, 255, 0.85);
  box-shadow: var(--app-shadow-md);
}
.org-detail-banner__title {
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  font-weight: 800;
  margin: 8px 0 4px;
  color: white;
  text-shadow: 0 2px 10px rgb(0 0 0 / 0.2);
}
.org-detail-banner__slug {
  margin: 0;
  opacity: 0.9;
  font-size: 0.9rem;
}
.org-detail-banner__chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.org-detail-banner__text .app-chip {
  background: rgba(255, 255, 255, 0.18);
  color: white;
  backdrop-filter: blur(6px);
}
.org-detail-banner__actions {
  align-self: flex-end;
}
.org-detail-section-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}
.exam-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: center;
}
.exam-card__icon {
  color: var(--q-primary);
}
.exam-card__name {
  margin: 0;
  font-weight: 700;
}
.exam-card__meta {
  font-size: 0.85rem;
}
@media (max-width: 640px) {
  .org-detail-banner__content {
    grid-template-columns: 1fr;
    text-align: left;
  }
  .org-detail-banner__actions {
    justify-self: start;
  }
}
</style>
