import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('pages/IndexPage.vue') },
      {
        path: 'login',
        name: 'login',
        component: () => import('pages/LoginPage.vue'),
      },
      {
        path: 'profile',
        name: 'profile',
        meta: { requiresAuth: true },
        component: () => import('pages/ProfilePage.vue'),
      },
      {
        path: 'orgs',
        name: 'orgs',
        meta: { requiresAuth: true },
        component: () => import('pages/OrgsPage.vue'),
      },
      {
        path: 'orgs/:slug',
        name: 'org-detail',
        meta: { requiresAuth: true },
        component: () => import('pages/OrgDetailPage.vue'),
      },
      {
        path: 'orgs/:slug/settings',
        name: 'org-settings',
        meta: { requiresAuth: true },
        component: () => import('pages/OrgSettingsPage.vue'),
      },
      {
        path: 'admin',
        name: 'admin',
        meta: { requiresAuth: true, requiresSuperuser: true },
        component: () => import('pages/AdminPage.vue'),
      },
    ],
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
