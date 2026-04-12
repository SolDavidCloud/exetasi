import { defineBoot } from '#q-app/wrappers';

import { initApiClient } from 'src/api/client';

export default defineBoot(() => {
  initApiClient();
});
