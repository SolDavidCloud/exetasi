import { defineBoot } from '#q-app/wrappers';

import { useThemeStore } from 'src/stores/theme-store';

export default defineBoot(() => {
  const theme = useThemeStore();
  theme.init();
});
