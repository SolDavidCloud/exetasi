<template>
  <q-page class="app-container q-py-xl">
    <PageHeader
      :title="t('admin.title')"
      :lead="t('admin.lead')"
    >
      <template #actions>
        <q-input
          v-model="search"
          dense
          outlined
          :placeholder="t('admin.searchPlaceholder')"
          :debounce="300"
          clearable
          @update:model-value="onSearch"
        >
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>
    </PageHeader>

    <section class="app-panel q-mb-lg">
      <header class="admin-section__header">
        <h2 class="admin-section__title">{{ t('admin.users.title') }}</h2>
        <p class="app-muted q-ma-none">{{ t('admin.users.lead') }}</p>
      </header>
      <q-separator class="q-my-md" />

      <q-table
        flat
        bordered
        :rows="admin.users"
        :columns="columns"
        row-key="id"
        :loading="admin.loading"
        :pagination="{ rowsPerPage: 25 }"
        :no-data-label="t('admin.users.empty')"
      >
        <template #body-cell-flags="props">
          <q-td :props="props">
            <div class="row q-gutter-xs">
              <q-chip
                v-if="props.row.is_superuser"
                dense
                color="primary"
                text-color="white"
                size="sm"
                icon="shield_person"
              >
                {{ t('admin.flags.superuser') }}
              </q-chip>
              <q-chip
                v-if="props.row.can_create_orgs && !props.row.is_superuser"
                dense
                color="secondary"
                text-color="white"
                size="sm"
                icon="add_business"
              >
                {{ t('admin.flags.canCreateOrgs') }}
              </q-chip>
              <q-chip
                v-if="props.row.is_banned"
                dense
                color="negative"
                text-color="white"
                size="sm"
                icon="block"
              >
                {{ t('admin.flags.banned') }}
              </q-chip>
            </div>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" auto-width>
            <q-btn flat dense round icon="more_vert">
              <q-menu auto-close>
                <q-list style="min-width: 220px">
                  <q-item
                    v-if="!props.row.is_superuser"
                    clickable
                    :disable="props.row.is_banned"
                    @click="onSetSuperuser(props.row, true)"
                  >
                    <q-item-section avatar>
                      <q-icon name="shield_person" />
                    </q-item-section>
                    <q-item-section>
                      {{ t('admin.actions.promote') }}
                    </q-item-section>
                  </q-item>
                  <q-item
                    v-else
                    clickable
                    :disable="props.row.id === auth.user?.id"
                    @click="onSetSuperuser(props.row, false)"
                  >
                    <q-item-section avatar>
                      <q-icon name="do_not_disturb" />
                    </q-item-section>
                    <q-item-section>
                      {{ t('admin.actions.demote') }}
                    </q-item-section>
                  </q-item>
                  <q-separator />
                  <q-item
                    v-if="!props.row.is_superuser"
                    clickable
                    @click="onToggleCreateOrgs(props.row, !props.row.can_create_orgs)"
                  >
                    <q-item-section avatar>
                      <q-icon
                        :name="props.row.can_create_orgs ? 'lock' : 'add_business'"
                      />
                    </q-item-section>
                    <q-item-section>
                      {{
                        props.row.can_create_orgs
                          ? t('admin.actions.disallowOrgs')
                          : t('admin.actions.allowOrgs')
                      }}
                    </q-item-section>
                  </q-item>
                  <q-separator />
                  <q-item
                    v-if="!props.row.is_banned"
                    clickable
                    :disable="props.row.is_superuser || props.row.id === auth.user?.id"
                    @click="openBanDialog(props.row)"
                  >
                    <q-item-section avatar>
                      <q-icon name="block" color="negative" />
                    </q-item-section>
                    <q-item-section>{{ t('admin.actions.ban') }}</q-item-section>
                  </q-item>
                  <q-item v-else clickable @click="onUnban(props.row)">
                    <q-item-section avatar>
                      <q-icon name="lock_open" />
                    </q-item-section>
                    <q-item-section>{{ t('admin.actions.unban') }}</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </q-btn>
          </q-td>
        </template>
      </q-table>
    </section>

    <section class="app-panel">
      <header class="admin-section__header">
        <h2 class="admin-section__title">{{ t('admin.orgs.title') }}</h2>
        <p class="app-muted q-ma-none">{{ t('admin.orgs.lead') }}</p>
      </header>
      <q-separator class="q-my-md" />

      <div class="column q-gutter-md" style="max-width: 520px">
        <q-input
          v-model="transferSlug"
          outlined
          :label="t('admin.orgs.slugLabel')"
          :hint="t('admin.orgs.slugHint')"
        />
        <q-input
          v-model="transferNewOwner"
          outlined
          :label="t('admin.orgs.newOwnerLabel')"
          :hint="t('admin.orgs.newOwnerHint')"
        />
        <q-btn
          unelevated
          color="primary"
          :label="t('admin.orgs.transferCta')"
          :disable="!transferSlug.trim() || !transferNewOwner.trim()"
          :loading="transferring"
          @click="onTransfer"
        />
      </div>
    </section>

    <q-dialog v-model="banDialogOpen">
      <q-card style="min-width: 360px; max-width: 420px; width: 100%">
        <q-card-section>
          <p class="text-h6 q-ma-none">
            {{ t('admin.banDialog.title', { username: banTarget?.username ?? '' }) }}
          </p>
          <p class="app-muted q-mt-xs q-mb-none">
            {{ t('admin.banDialog.lead') }}
          </p>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="banReason"
            outlined
            autofocus
            type="textarea"
            autogrow
            :label="t('admin.banDialog.reason')"
            :maxlength="500"
            counter
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('actions.cancel')" v-close-popup />
          <q-btn
            unelevated
            color="negative"
            :label="t('admin.actions.ban')"
            :loading="banning"
            @click="onConfirmBan"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import type { QTableColumn } from 'quasar';

import PageHeader from 'components/PageHeader.vue';
import { useAdminStore, type AdminUser } from 'src/stores/admin-store';
import { useAuthStore } from 'src/stores/auth-store';

const { t } = useI18n();
const $q = useQuasar();
const admin = useAdminStore();
const auth = useAuthStore();

const search = ref('');

const banDialogOpen = ref(false);
const banTarget = ref<AdminUser | null>(null);
const banReason = ref('');
const banning = ref(false);

const transferSlug = ref('');
const transferNewOwner = ref('');
const transferring = ref(false);

const columns: QTableColumn<AdminUser>[] = [
  {
    name: 'username',
    label: t('admin.cols.username'),
    align: 'left',
    field: (row: AdminUser) => row.username,
    sortable: true,
  },
  {
    name: 'flags',
    label: t('admin.cols.flags'),
    align: 'left',
    field: 'id',
  },
  {
    name: 'banReason',
    label: t('admin.cols.banReason'),
    align: 'left',
    field: (row: AdminUser) => row.ban_reason ?? '',
  },
  {
    name: 'actions',
    label: t('admin.cols.actions'),
    align: 'right',
    field: 'id',
  },
];

async function onSearch(value: string | number | null): Promise<void> {
  const q = typeof value === 'string' ? value.trim() : '';
  await admin.fetchUsers(q);
}

async function onSetSuperuser(row: AdminUser, value: boolean): Promise<void> {
  const updated = await admin.setSuperuser(row.username, value);
  if (!updated) {
    $q.notify({ type: 'negative', message: t('admin.errors.generic') });
    return;
  }
  $q.notify({
    type: 'positive',
    message: value
      ? t('admin.messages.promoted', { username: row.username })
      : t('admin.messages.demoted', { username: row.username }),
  });
}

async function onToggleCreateOrgs(row: AdminUser, allowed: boolean): Promise<void> {
  const updated = await admin.setCanCreateOrgs(row.username, allowed);
  if (!updated) {
    $q.notify({ type: 'negative', message: t('admin.errors.generic') });
    return;
  }
  $q.notify({
    type: 'positive',
    message: allowed
      ? t('admin.messages.orgsAllowed', { username: row.username })
      : t('admin.messages.orgsDisallowed', { username: row.username }),
  });
}

function openBanDialog(row: AdminUser): void {
  banTarget.value = row;
  banReason.value = '';
  banDialogOpen.value = true;
}

async function onConfirmBan(): Promise<void> {
  if (!banTarget.value) return;
  banning.value = true;
  try {
    const updated = await admin.banUser(banTarget.value.username, banReason.value.trim());
    if (!updated) {
      $q.notify({ type: 'negative', message: t('admin.errors.generic') });
      return;
    }
    $q.notify({
      type: 'positive',
      message: t('admin.messages.banned', { username: banTarget.value.username }),
    });
    banDialogOpen.value = false;
  } finally {
    banning.value = false;
  }
}

async function onUnban(row: AdminUser): Promise<void> {
  const updated = await admin.unbanUser(row.username);
  if (!updated) {
    $q.notify({ type: 'negative', message: t('admin.errors.generic') });
    return;
  }
  $q.notify({
    type: 'positive',
    message: t('admin.messages.unbanned', { username: row.username }),
  });
}

async function onTransfer(): Promise<void> {
  transferring.value = true;
  try {
    const ok = await admin.transferOwner(
      transferSlug.value.trim(),
      transferNewOwner.value.trim(),
    );
    if (!ok) {
      $q.notify({ type: 'negative', message: t('admin.errors.transfer') });
      return;
    }
    $q.notify({ type: 'positive', message: t('admin.messages.transferred') });
    transferSlug.value = '';
    transferNewOwner.value = '';
  } finally {
    transferring.value = false;
  }
}

onMounted(() => {
  void admin.fetchUsers();
});
</script>

<style scoped lang="scss">
.admin-section__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.admin-section__title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}
</style>
