<template>
  <q-page class="app-container q-py-xl">
    <PageHeader :title="t('orgs.title')" :lead="t('orgs.lead')">
      <template #actions>
        <q-btn
          v-if="auth.canCreateOrgs"
          unelevated
          color="primary"
          icon="add"
          :label="t('orgs.createCta')"
          @click="showCreate = true"
        />
      </template>
    </PageHeader>

    <div v-if="!auth.canCreateOrgs" class="app-panel app-panel--muted q-mb-md" role="status">
      <div class="row items-center q-gutter-sm">
        <q-icon name="lock" size="20px" color="primary" />
        <p class="q-ma-none">{{ t('orgs.createLockedLead') }}</p>
      </div>
    </div>

    <EmptyState
      v-if="!loading && orgs.list.length === 0"
      icon="groups"
      :title="t('orgs.emptyTitle')"
      :description="t('orgs.emptyDescription')"
    >
      <q-btn
        v-if="auth.canCreateOrgs"
        unelevated
        color="primary"
        icon="add"
        :label="t('orgs.createCta')"
        @click="showCreate = true"
      />
    </EmptyState>

    <div v-else class="app-grid">
      <router-link
        v-for="o in orgs.list"
        :key="o.id"
        class="org-card app-panel app-card-hover"
        :to="{ name: 'org-detail', params: { slug: o.slug } }"
        :style="orgStyle(o)"
      >
        <OrgBanner :banner-url="o.banner_url" compact />
        <div class="org-card__body">
          <OrgAvatar
            class="org-card__avatar"
            :name="o.name"
            :avatar-url="o.avatar_url"
            :primary-color="o.primary_color"
            :secondary-color="o.secondary_color"
            :size="56"
          />
          <div class="org-card__text">
            <p class="org-card__name">{{ o.name }}</p>
            <p class="org-card__slug app-muted">{{ o.slug }}</p>
            <p v-if="o.description" class="org-card__desc app-muted">
              {{ o.description }}
            </p>
          </div>
          <div class="org-card__badges">
            <q-chip
              v-if="o.is_personal"
              dense
              color="primary"
              text-color="white"
              size="sm"
              class="org-card__badge"
            >
              {{ t('orgs.personalBadge') }}
            </q-chip>
            <q-chip
              v-else
              dense
              outline
              color="primary"
              size="sm"
              class="org-card__badge"
            >
              {{ t(`orgs.roles.${o.role}`) }}
            </q-chip>
          </div>
        </div>
      </router-link>
    </div>

    <q-dialog v-model="showCreate">
      <q-card style="min-width: 360px; max-width: 420px; width: 100%">
        <q-card-section>
          <p class="text-h6 q-ma-none">{{ t('orgs.createTitle') }}</p>
          <p class="app-muted q-mt-xs q-mb-none">{{ t('orgs.createLead') }}</p>
        </q-card-section>
        <q-card-section class="column q-gutter-md">
          <q-input
            v-model="newName"
            outlined
            autofocus
            :label="t('orgs.name')"
            :rules="[(v) => !!v || t('orgs.nameRequired')]"
          />
          <q-input
            v-model="newDescription"
            outlined
            type="textarea"
            autogrow
            :label="t('orgs.description')"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('actions.cancel')" v-close-popup />
          <q-btn
            unelevated
            color="primary"
            :label="t('orgs.create')"
            :loading="creating"
            :disable="newName.trim().length === 0"
            @click="createOrg"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import EmptyState from 'components/EmptyState.vue';
import OrgAvatar from 'components/OrgAvatar.vue';
import OrgBanner from 'components/OrgBanner.vue';
import PageHeader from 'components/PageHeader.vue';
import { useAuthStore } from 'src/stores/auth-store';
import { useOrgsStore, type Organization } from 'src/stores/orgs-store';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const orgs = useOrgsStore();
const auth = useAuthStore();

const showCreate = ref(false);
const newName = ref('');
const newDescription = ref('');
const creating = ref(false);

const loading = computed(() => orgs.loading);

function orgStyle(o: Organization): Record<string, string> {
  const vars: Record<string, string> = {};
  if (o.primary_color) {
    vars['--q-primary'] = o.primary_color;
    vars['--app-brand-soft'] = `color-mix(in srgb, ${o.primary_color} 14%, transparent)`;
  }
  if (o.secondary_color) vars['--q-secondary'] = o.secondary_color;
  if (o.accent_color) vars['--q-accent'] = o.accent_color;
  return vars;
}

async function createOrg() {
  creating.value = true;
  try {
    const created = await orgs.create({
      name: newName.value.trim(),
      description: newDescription.value.trim(),
    });
    if (!created) {
      $q.notify({ type: 'negative', message: t('orgs.createFailed') });
      return;
    }
    $q.notify({ type: 'positive', message: t('orgs.createSuccess') });
    showCreate.value = false;
    newName.value = '';
    newDescription.value = '';
    await router.push({ name: 'org-detail', params: { slug: created.slug } });
  } finally {
    creating.value = false;
  }
}

onMounted(() => {
  void orgs.fetchAll();
});
</script>

<style scoped lang="scss">
.org-card {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  text-decoration: none;
  color: inherit;
  overflow: hidden;
}
.org-card:hover {
  text-decoration: none;
}
.org-card__body {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 16px 20px 20px;
}
.org-card__avatar {
  margin-top: -36px;
  border: 3px solid var(--app-surface);
}
.org-card__text {
  min-width: 0;
}
.org-card__name {
  font-weight: 700;
  font-size: 1.05rem;
  margin: 0;
}
.org-card__slug {
  margin: 0;
  font-size: 0.85rem;
}
.org-card__desc {
  margin: 6px 0 0;
  font-size: 0.9rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}
.org-card__badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.org-card__badge {
  align-self: flex-end;
}
</style>
