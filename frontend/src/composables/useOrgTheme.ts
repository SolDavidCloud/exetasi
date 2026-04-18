import { computed, type MaybeRefOrGetter, toValue } from 'vue';

import type { Organization } from 'src/stores/orgs-store';

export interface OrgThemeVars {
  '--q-primary'?: string;
  '--q-secondary'?: string;
  '--q-accent'?: string;
  // App-specific derived tokens so non-Quasar surfaces pick up the palette too.
  '--app-brand-soft'?: string;
  '--app-brand-softer'?: string;
}

/**
 * Produces a style object you can bind to a root `<div :style="styles">`
 * wrapper to scope an organization's palette to that subtree only.
 *
 * Any colour the org hasn't set falls back to the app defaults defined in
 * `quasar.variables.scss` / `app.scss`, so partial customisation is safe.
 */
export function useOrgTheme(
  orgRef: MaybeRefOrGetter<Pick<
    Organization,
    'primary_color' | 'secondary_color' | 'accent_color'
  > | null | undefined>,
) {
  const styles = computed<Record<string, string>>(() => {
    const org = toValue(orgRef);
    if (!org) {
      return {};
    }
    const vars: Record<string, string> = {};
    if (org.primary_color) {
      vars['--q-primary'] = org.primary_color;
      vars['--app-brand-soft'] = `color-mix(in srgb, ${org.primary_color} 14%, transparent)`;
      vars['--app-brand-softer'] = `color-mix(in srgb, ${org.primary_color} 7%, transparent)`;
    }
    if (org.secondary_color) {
      vars['--q-secondary'] = org.secondary_color;
    }
    if (org.accent_color) {
      vars['--q-accent'] = org.accent_color;
    }
    return vars;
  });

  return { styles };
}
