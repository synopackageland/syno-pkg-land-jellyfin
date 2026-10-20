import {dsmLoginSetup} from '@synopackageland/cli/e2e';
dsmLoginSetup({session:'admin',user:'admin',timeout:240_000});
dsmLoginSetup({session:'user',user:'reader',timeout:240_000});
