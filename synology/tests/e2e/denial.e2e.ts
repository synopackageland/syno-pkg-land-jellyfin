import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
import {dsmPage,openDesktop,registerDsmSecrets} from '@synopackageland/cli/e2e';

// An administrator must deny this fixture account only this package's App
// privilege and restore the exact previous rule afterward. Never mutate accounts.
test('denied DSM App privilege returns 403',{
 session:'user',skip:process.env.JELLYFIN_E2E_DENIED!=='1',
},async({app})=>{
 await openDesktop(app);const page=dsmPage();await registerDsmSecrets(page);
 const context=page.context();
 await context.clearCookies({name:'synopkgland_sso_SynoPkgJellyfin'});
 const entry=await context.request.get(new URL('/',process.env.JELLYFIN_E2E_URL!).href,{
  headers:{Accept:'text/html','Sec-Fetch-Mode':'navigate'},maxRedirects:0,ignoreHTTPSErrors:true,
 });
 expect(entry.status()).toBe(302);
 const authorize=new URL(entry.headers()['location']);
 // The test uses an SSH-forwarded DSM origin; retain the issued path and query.
 const dsm=new URL(process.env.DSM_E2E_URL!);
 authorize.protocol=dsm.protocol;authorize.host=dsm.host;
 const [refused]=await Promise.all([
  page.waitForResponse(response=>new URL(response.url()).pathname==='/_sso/dsm-return',{timeout:30_000}),
  page.goto(authorize.href),
 ]);
 expect(refused.status()).toBe(403);
 expect(await refused.text()).toContain('data-error-code="dsm_app_privilege_denied"');
});
