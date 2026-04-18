<template>
  <q-page class="app-container app-container--narrow q-py-xl">
    <q-btn
      flat
      dense
      color="primary"
      icon="arrow_back"
      class="q-mb-md"
      :to="{ name: 'org-detail', params: { slug } }"
      :label="t('orgs.settings.back')"
    />

    <PageHeader
      :title="t('orgs.settings.title')"
      :lead="t('orgs.settings.lead')"
      :eyebrow="org?.name ?? ''"
    />

    <!-- Role-aware guard: render the editor only to owners. Hide the form
         from non-owners even though the backend already enforces the rule,
         so they see a sensible explanation instead of a 403 toast. -->
    <div v-if="org && !canEdit" class="q-mt-lg">
      <EmptyState
        icon="lock"
        :title="t('orgs.settings.forbiddenTitle')"
        :description="t('orgs.settings.forbiddenDesc')"
      >
        <q-btn
          unelevated
          color="primary"
          icon="arrow_back"
          :label="t('orgs.settings.back')"
          :to="{ name: 'org-detail', params: { slug } }"
        />
      </EmptyState>
    </div>

    <div v-else-if="org" :style="themeStyles" class="column q-gutter-md">
      <section class="app-panel column q-gutter-md">
        <p class="section-head">{{ t('orgs.settings.basics') }}</p>
        <q-input
          v-model="draft.name"
          outlined
          :label="t('orgs.name')"
          :rules="[(v) => !!v || t('orgs.nameRequired')]"
        />
        <q-input
          v-if="!org.is_personal"
          v-model="draft.slug"
          outlined
          :label="t('orgs.slug')"
          :hint="t('orgs.slugHint')"
        />
        <q-banner v-else class="app-panel app-panel--plain text-caption">
          {{ t('orgs.slugPersonalLocked') }}
        </q-banner>
        <q-input
          v-model="draft.description"
          outlined
          type="textarea"
          autogrow
          :label="t('orgs.description')"
        />
      </section>

      <section class="app-panel column q-gutter-md">
        <p class="section-head">{{ t('orgs.settings.identity') }}</p>
        <p class="app-muted q-mt-xs q-mb-sm">{{ t('orgs.settings.identityLead') }}</p>

        <div class="identity-preview">
          <OrgAvatar
            :name="draft.name || org.name"
            :avatar-url="draft.avatar_url"
            :primary-color="draft.primary_color"
            :secondary-color="draft.secondary_color"
            :size="72"
          />
          <div class="identity-preview__text">
            <p class="text-weight-bold q-ma-none">{{ draft.name || org.name }}</p>
            <p class="app-muted q-ma-none">{{ t('orgs.settings.previewHint') }}</p>
          </div>
        </div>

        <q-input
          v-model="draft.avatar_url"
          outlined
          :label="t('orgs.settings.iconUrl')"
          :hint="t('orgs.settings.iconUrlHint')"
          placeholder="https://…"
        />

        <q-input
          v-model="draft.banner_url"
          outlined
          :label="t('orgs.settings.bannerUrl')"
          :hint="t('orgs.settings.bannerUrlHint')"
          placeholder="https://…"
        />

        <OrgBanner :banner-url="draft.banner_url" class="banner-preview" />
      </section>

      <section class="app-panel column q-gutter-md">
        <p class="section-head">{{ t('orgs.settings.palette') }}</p>
        <p class="app-muted q-mt-xs q-mb-sm">{{ t('orgs.settings.paletteLead') }}</p>

        <ColorPaletteField v-model="draft.primary_color" :label="t('theme.primary')" />
        <ColorPaletteField
          v-model="draft.secondary_color"
          :label="t('theme.secondary')"
          fallback="#0ea5a4"
        />
        <ColorPaletteField
          v-model="draft.accent_color"
          :label="t('theme.accent')"
          fallback="#f59e0b"
        />

        <div class="palette-preview">
          <q-btn unelevated color="primary" :label="t('theme.preview.primary')" />
          <q-btn unelevated color="secondary" :label="t('theme.preview.secondary')" />
          <q-btn unelevated color="accent" :label="t('theme.preview.accent')" />
          <q-btn flat color="primary" :label="t('theme.preview.flat')" />
        </div>
      </section>

      <div class="row justify-end q-gutter-sm">
        <q-btn flat :label="t('actions.reset')" :disable="!dirty" @click="reset" />
        <q-btn
          unelevated
          color="primary"
          :loading="saving"
          :disable="!dirty"
          icon="save"
          :label="t('actions.save')"
          @click="save"
        />
      </div>

      <AlertsCrudPanel
        kind="org"
        :org-slug="org.slug"
        :title="t('orgs.settings.alerts.title')"
        :lead="t('orgs.settings.alerts.lead')"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';

import AlertsCrudPanel from 'components/AlertsCrudPanel.vue';
import ColorPaletteField from 'components/ColorPaletteField.vue';
import EmptyState from 'components/EmptyState.vue';
import OrgAvatar from 'components/OrgAvatar.vue';
import OrgBanner from 'components/OrgBanner.vue';
import PageHeader from 'components/PageHeader.vue';
import { useOrgTheme } from 'src/composables/useOrgTheme';
import { useOrgsStore, type Organization, type OrganizationUpdate } from 'src/stores/orgs-store';

interface DraftState {
  name: string;
  slug: string;
  description: string;
  avatar_url: string | null;
  banner_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  accent_color: string | null;
}

const { t } = useI18n();
const $q = useQuasar();
const route = useRoute();
const orgs = useOrgsStore();

const slug = computed(() => String(route.params.slug ?? ''));
const org = computed<Organization | null>(() => orgs.get(slug.value) ?? null);
const canEdit = computed(() => orgs.isOwner(slug.value));
const { styles: themeStyles } = useOrgTheme(() => ({
  primary_color: draft.primary_color,
  secondary_color: draft.secondary_color,
  accent_color: draft.accent_color,
}));

const saving = ref(false);
const draft = reactive<DraftState>({
  name: '',
  slug: '',
  description: '',
  avatar_url: null,
  banner_url: null,
  primary_color: null,
  secondary_color: null,
  accent_color: null,
});

function hydrate(from: Organization): void {
  draft.name = from.name;
  draft.slug = from.slug;
  draft.description = from.description ?? '';
  draft.avatar_url = from.avatar_url;
  draft.banner_url = from.banner_url;
  draft.primary_color = from.primary_color;
  draft.secondary_color = from.secondary_color;
  draft.accent_color = from.accent_color;
}

const dirty = computed(() => {
  const current = org.value;
  if (!current) return false;
  return (
    current.name !== draft.name ||
    current.slug !== draft.slug ||
    (current.description ?? '') !== draft.description ||
    (current.avatar_url ?? null) !== (draft.avatar_url ?? null) ||
    (current.banner_url ?? null) !== (draft.banner_url ?? null) ||
    (current.primary_color ?? null) !== (draft.primary_color ?? null) ||
    (current.secondary_color ?? null) !== (draft.secondary_color ?? null) ||
    (current.accent_color ?? null) !== (draft.accent_color ?? null)
  );
});

function reset(): void {
  if (org.value) hydrate(org.value);
}

async function save(): Promise<void> {
  if (!org.value) return;
  const payload: OrganizationUpdate = {
    name: draft.name.trim(),
    description: draft.description,
    avatar_url: draft.avatar_url ?? '',
    banner_url: draft.banner_url ?? '',
    primary_color: draft.primary_color,
    secondary_color: draft.secondary_color,
    accent_color: draft.accent_color,
  };
  if (!org.value.is_personal && draft.slug !== org.value.slug) {
    payload.slug = draft.slug;
  }
  saving.value = true;
  try {
    const updated = await orgs.update(org.value.slug, payload);
    if (!updated) {
      $q.notify({ type: 'negative', message: t('orgs.settings.saveFailed') });
      return;
    }
    hydrate(updated);
    $q.notify({ type: 'positive', message: t('orgs.settings.saveSuccess') });
  } finally {
    saving.value = false;
  }
}

async function load(): Promise<void> {
  const fetched = await orgs.fetchOne(slug.value);
  if (fetched) hydrate(fetched);
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
.section-head {
  font-weight: 700;
  font-size: 1.05rem;
  margin: 0;
}
.identity-preview {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  background: var(--app-surface-muted);
  border-radius: var(--app-radius-md);
}
.banner-preview {
  margin-top: 4px;
}
.palette-preview {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 4px;
}
</style>
