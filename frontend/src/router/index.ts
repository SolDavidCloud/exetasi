import { defineRouter } from '#q-app/wrappers';
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router';
import routes from './routes';
import { useAuthStore } from 'src/stores/auth-store';

/*
 * If not building with SSR mode, you can
 * directly export the Router instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Router instance.
 */

export default defineRouter((/* { store, ssrContext } */) => {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : (process.env.VUE_ROUTER_MODE === 'history' ? createWebHistory : createWebHashHistory);

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,

    // Leave this as is and make changes in quasar.conf.js instead!
    // quasar.conf.js -> build -> vueRouterMode
    // quasar.conf.js -> build -> publicPath
    history: createHistory(process.env.VUE_ROUTER_BASE),
  });

  Router.beforeEach(async (to) => {
    const auth = useAuthStore();
    if (!auth.loaded) {
      await auth.fetchSession();
    }
    if (to.meta.requiresAuth === true && !auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } };
    }
    if (to.meta.requiresSuperuser === true && !auth.isSuperuser) {
      // Non-super-users are bounced to the 404 page, matching the API's
      // "404 on the admin surface" policy so we don't leak its existence.
      return { name: 'home' };
    }
    return true;
  });

  return Router;
});
