import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
import {dsmPage,openDesktop,registerDsmSecrets} from '@synopackageland/cli/e2e';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';

for(const [session,admin] of [['admin',true],['user',false]] as const){
 test(`DSM menu and one-click SSO create the native ${session} session`,
  {session,timeout:150_000},async({app})=>{
   await openDesktop(app);
   const desktop=dsmPage();await registerDsmSecrets(desktop);
   await desktop.locator('#sds-taskbar button.start-button-img').click();
   let [page]=await Promise.all([
    desktop.context().waitForEvent('page',{timeout:30_000}),
    desktop.getByRole('menuitem',{name:'Jellyfin',exact:true}).click(),
   ]);
   console.log('DSM menu entry opened');
   const signIn=page.getByRole('button',{name:'Sign in with DSM',exact:true});
   const userMenu=page.getByRole('button',{name:'User Menu',exact:true});
   await signIn.or(userMenu).first().waitFor({timeout:30_000});
   const existing=await userMenu.isVisible();
   if(existing){
    await page.getByRole('button',{name:'User Menu',exact:true}).click();
    await page.getByRole('menuitem',{name:'Sign Out',exact:true}).click();
   }
   await page.getByRole('button',{name:'Sign in with DSM',exact:true}).click({timeout:45_000});
   console.log('Native SSO requested');
   await page.waitForFunction(()=>{
    const raw=localStorage.getItem('jellyfin_credentials');
    return location.pathname.startsWith('/web/') && Boolean((window as any).ApiClient?.getCurrentUserId?.()) && raw && JSON.parse(raw).Servers?.[0]?.AccessToken;
   },undefined,{timeout:45_000});
   console.log('Native token established');
   const user=await page.evaluate(async()=>{
    const server=JSON.parse(localStorage.getItem('jellyfin_credentials')!).Servers[0];
    const response=await fetch('/Users/Me',{headers:{Authorization:`MediaBrowser Token=${server.AccessToken}`}});
    if(!response.ok)throw new Error(`Native user read failed: ${response.status}`);
    const u=await response.json();return {id:u.Id,subject:u.Name,admin:u.Policy?.IsAdministrator};
   });
   expect(/^\d+$/.test(user.subject),'JIT uses signed sub/UID as the native username').toBe(true);
   expect(user.admin).toBe(admin);
   if(!admin){
    const administrator=JSON.parse(await readFile(join(process.env.DSM_E2E_OUTPUT_DIR!,'identity-admin.json'),'utf8'));
    expect(user.id).not.toBe(administrator.id);expect(user.subject).not.toBe(administrator.subject);
   }
   await writeFile(join(process.env.DSM_E2E_OUTPUT_DIR!,`identity-${session}.json`),JSON.stringify(user)+'\n',{mode:0o600});
   console.log('Native user verified');
   await page.waitForFunction(()=>location.pathname.startsWith('/web/'));
   console.log('Native web route reached');
   await page.getByRole('button',{name:'User Menu',exact:true}).waitFor({timeout:30_000});
   await page.screenshot({path:join(process.env.DSM_E2E_OUTPUT_DIR!,`menu-${session}.png`)});
   console.log('Native home rendered');
   const media=await page.evaluate(async()=>{
    const server=JSON.parse(localStorage.getItem('jellyfin_credentials')!).Servers[0];
    const headers={Authorization:`MediaBrowser Token=${server.AccessToken}`};
    const response=await fetch(`/Users/${server.UserId}/Items?Recursive=true&IncludeItemTypes=Movie`,{headers});
    const items=await response.json();let item;
    for(const candidate of items.Items ?? [])if(candidate.Name==='SSO Fixture')item=candidate;
    if(!item)throw new Error('The selected read-only media fixture was not indexed');
    const stream=await fetch(`/Videos/${item.Id}/stream?static=true`,{headers:{...headers,Range:'bytes=0-4095'}});
    const bytes=new Uint8Array(await stream.arrayBuffer());
    const transcode=await fetch(`/Videos/${item.Id}/stream.mp4?static=false&VideoCodec=h264&AudioCodec=aac&VideoBitRate=150000&AudioBitRate=64000&MaxWidth=160&MaxHeight=90&TranscodingMaxAudioChannels=2`,{headers});
    const encoded=new Uint8Array(await transcode.arrayBuffer());
    return {status:stream.status,bytes:bytes.length,mp4:String.fromCharCode(...bytes.slice(4,8)),transcodeStatus:transcode.status,transcodeBytes:encoded.length,transcodeMp4:String.fromCharCode(...encoded.slice(4,8))};
   });
   expect(media.status).toBe(206);expect(media.bytes).toBe(4096);expect(media.mp4).toBe('ftyp');
   expect(media.transcodeStatus).toBe(200);expect(media.transcodeBytes).toBeGreaterThan(0);expect(media.transcodeMp4).toBe('ftyp');
   await page.getByRole('button',{name:'User Menu',exact:true}).click();
   await page.getByRole('menuitem',{name:'Sign Out',exact:true}).click();
   await page.getByRole('button',{name:'Sign in with DSM',exact:true}).waitFor({timeout:20_000});
   await page.close();
   await desktop.locator('#sds-taskbar button.start-button-img').click();
   [page]=await Promise.all([
    desktop.context().waitForEvent('page',{timeout:30_000}),
    desktop.getByRole('menuitem',{name:'Jellyfin',exact:true}).click(),
   ]);
   await page.getByRole('button',{name:'Sign in with DSM',exact:true}).click({timeout:30_000});
   await page.waitForFunction(id=>{
    const raw=localStorage.getItem('jellyfin_credentials');
    return location.pathname.startsWith('/web/') && Boolean((window as any).ApiClient?.getCurrentUserId?.()) && raw && JSON.parse(raw).Servers?.[0]?.UserId===id && JSON.parse(raw).Servers?.[0]?.AccessToken;
   },user.id,{timeout:45_000});
   await page.close();
 });
}
test('requests without a DSM session are refused',{session:'admin'},async({app})=>{
 await openDesktop(app);const page=dsmPage();
 const context=await page.context().browser()!.newContext({ignoreHTTPSErrors:true});
 try{
  const response=await context.request.get(new URL('/Users/Me',process.env.JELLYFIN_E2E_URL!).href,{maxRedirects:0});
  expect(response.status()).toBe(401);
 }finally{await context.close();}
});
