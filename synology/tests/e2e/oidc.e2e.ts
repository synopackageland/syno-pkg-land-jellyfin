import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
import {dsmPage,openDesktop,registerDsmSecrets} from '@synopackageland/cli/e2e';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const basePath = '/synopkgland/SynoPkgJellyfin';

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
   const assetFailures: string[]=[];
   page.on('response',response=>{
    const request=response.request();
    const url=new URL(response.url());
    if(['script','stylesheet'].includes(request.resourceType()) &&
       (request.headers()['referer'] ?? '').includes(basePath+'/') &&
       (!url.pathname.startsWith(basePath+'/') || response.status()>=400)){
     assetFailures.push(`${response.status()} ${url.pathname}`);
    }
   });
   const network=await page.context().newCDPSession(page);
   await network.send('Network.enable');
   const socketPaths=new Map<string,string>();
   const socketStatuses: number[]=[];
   network.on('Network.webSocketCreated',event=>{
    socketPaths.set(event.requestId,new URL(event.url).pathname);
   });
   network.on('Network.webSocketHandshakeResponseReceived',event=>{
    if(socketPaths.get(event.requestId)===basePath+'/socket')socketStatuses.push(event.response.status);
   });
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
   await page.waitForFunction(base=>{
    const raw=localStorage.getItem('jellyfin_credentials');
    return location.pathname.startsWith(base+'/web/') && Boolean((window as any).ApiClient?.getCurrentUserId?.()) && raw && JSON.parse(raw).Servers?.[0]?.AccessToken;
   },basePath,{timeout:45_000});
   console.log('Native token established');
   const user=await page.evaluate(async base=>{
    const server=JSON.parse(localStorage.getItem('jellyfin_credentials')!).Servers[0];
    const response=await fetch(base+'/Users/Me',{headers:{Authorization:`MediaBrowser Token=${server.AccessToken}`}});
    if(!response.ok)throw new Error(`Native user read failed: ${response.status}`);
    const u=await response.json();return {id:u.Id,subject:u.Name,admin:u.Policy?.IsAdministrator};
   },basePath);
   expect(/^\d+$/.test(user.subject),'JIT uses signed sub/UID as the native username').toBe(true);
   expect(user.admin).toBe(admin);
   if(!admin){
    const administrator=JSON.parse(await readFile(join(process.env.DSM_E2E_OUTPUT_DIR!,'identity-admin.json'),'utf8'));
    expect(user.id).not.toBe(administrator.id);expect(user.subject).not.toBe(administrator.subject);
   }
   await writeFile(join(process.env.DSM_E2E_OUTPUT_DIR!,`identity-${session}.json`),JSON.stringify(user)+'\n',{mode:0o600});
   console.log('Native user verified');
   await page.waitForFunction(base=>location.pathname.startsWith(base+'/web/'),basePath);
   console.log('Native web route reached');
   await page.getByRole('button',{name:'User Menu',exact:true}).waitFor({timeout:30_000});
   await page.screenshot({path:join(process.env.DSM_E2E_OUTPUT_DIR!,`menu-${session}.png`)});
   console.log('Native home rendered');
   await page.evaluate(base=>new Promise<void>((resolve,reject)=>{
    const server=JSON.parse(localStorage.getItem('jellyfin_credentials')!).Servers[0];
    const url=new URL(base+'/socket',location.href);
    url.protocol=location.protocol==='https:'?'wss:':'ws:';
    url.searchParams.set('ApiKey',server.AccessToken);
    url.searchParams.set('deviceId',localStorage.getItem('_deviceId2')!);
    const socket=new WebSocket(url);
    const timer=setTimeout(()=>{socket.close();reject(new Error('Native WebSocket did not open'));},30_000);
    socket.onopen=()=>{clearTimeout(timer);socket.close();resolve();};
    socket.onerror=()=>{clearTimeout(timer);reject(new Error('Native WebSocket failed'));};
   }),basePath);
   expect(socketStatuses).toContain(101);
   expect(assetFailures).toEqual([]);
   await writeFile(join(process.env.DSM_E2E_OUTPUT_DIR!,`network-${session}.json`),JSON.stringify({socketStatuses,assetFailures})+'\n');
   const media=await page.evaluate(async ({base,fixture})=>{
    const server=JSON.parse(localStorage.getItem('jellyfin_credentials')!).Servers[0];
    const headers={Authorization:`MediaBrowser Token=${server.AccessToken}`};
    const response=await fetch(`${base}/Users/${server.UserId}/Items?Recursive=true&IncludeItemTypes=Movie`,{headers});
    const items=await response.json();let item;
    for(const candidate of items.Items ?? [])if(candidate.Name===fixture)item=candidate;
    if(!item)throw new Error('The selected read-only media fixture was not indexed');
    const stream=await fetch(`${base}/Videos/${item.Id}/stream?static=true`,{headers:{...headers,Range:'bytes=0-4095'}});
    const bytes=new Uint8Array(await stream.arrayBuffer());
    const transcode=await fetch(`${base}/Videos/${item.Id}/stream.mp4?static=false&VideoCodec=h264&AudioCodec=aac&VideoBitRate=150000&AudioBitRate=64000&MaxWidth=160&MaxHeight=90&TranscodingMaxAudioChannels=2`,{headers});
    const encoded=new Uint8Array(await transcode.arrayBuffer());
    return {status:stream.status,bytes:bytes.length,mp4:String.fromCharCode(...bytes.slice(4,8)),transcodeStatus:transcode.status,transcodeBytes:encoded.length,transcodeMp4:String.fromCharCode(...encoded.slice(4,8))};
   },{base:basePath,fixture:process.env.JELLYFIN_E2E_MEDIA_NAME ?? 'SSO Fixture'});
   expect(media.status).toBe(206);expect(media.bytes).toBe(4096);expect(media.mp4).toBe('ftyp');
   expect(media.transcodeStatus).toBe(200);expect(media.transcodeBytes).toBeGreaterThan(0);expect(media.transcodeMp4).toBe('ftyp');
   await page.screenshot({path:join(process.env.DSM_E2E_OUTPUT_DIR!,`menu-${session}.png`)});
   await page.getByText('Media',{exact:true}).filter({visible:true}).first().click({timeout:30_000});
   await page.getByText(process.env.JELLYFIN_E2E_MEDIA_NAME ?? 'SSO Fixture',{exact:true}).filter({visible:true}).first().waitFor({timeout:30_000});
   await page.screenshot({path:join(process.env.DSM_E2E_OUTPUT_DIR!,`library-${session}.png`)});
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
   await page.waitForFunction(({id,base})=>{
    const raw=localStorage.getItem('jellyfin_credentials');
    return location.pathname.startsWith(base+'/web/') && Boolean((window as any).ApiClient?.getCurrentUserId?.()) && raw && JSON.parse(raw).Servers?.[0]?.UserId===id && JSON.parse(raw).Servers?.[0]?.AccessToken;
   },{id:user.id,base:basePath},{timeout:45_000});
   await page.close();
 });
}
test('requests without a DSM session are refused',{session:'admin'},async({app})=>{
 await openDesktop(app);const page=dsmPage();
 const context=await page.context().browser()!.newContext({ignoreHTTPSErrors:true});
 try{
  const response=await context.request.get(new URL(basePath+'/Users/Me',process.env.JELLYFIN_E2E_URL!).href,{maxRedirects:0});
  expect(response.status()).toBe(401);
 }finally{await context.close();}
});
