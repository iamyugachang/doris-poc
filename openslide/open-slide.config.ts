import type { OpenSlideConfig } from '@open-slide/core';

// Hosted under https://…run.app/deck/ (see deploy/nginx.conf); dev server ignores base.
const openSlideConfig: OpenSlideConfig = { base: '/deck/' };

export default openSlideConfig;
