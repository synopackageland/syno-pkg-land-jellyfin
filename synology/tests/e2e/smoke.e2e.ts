import { appOpenSmoke } from '@synopackageland/cli/e2e';

// Jellyfin's native login page renders after the DSM entry gate admits the user.
appOpenSmoke({ ready: '#loginPage' });
