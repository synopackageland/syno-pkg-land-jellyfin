#!/usr/bin/env node
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
export function nextVersion(current,tag,build){
 const match=/^v?((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?)$/.exec(tag??'');
 if(!match||!/^[1-9][0-9]{0,3}$/.test(build??''))throw new Error('Use a stable [v]X.Y[.Z] tag and build 1–9999.');
 const version=match[1];const number=Number(build);
 const parts=v=>v.split('.').map(Number);const a=parts(version),b=parts(current.version);
 let order=0;for(let n=0;n<Math.max(a.length,b.length);n++){order=(a[n]??0)-(b[n]??0);if(order)break;}
 if(order<0)throw new Error('Upstream downgrade is not supported.');
 if(version===current.version?number<=current.build:number!==1)throw new Error('Increase builds within one release; a new release starts at 0001.');
 return {version,build:number};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const file=new URL('./dsm-package.yaml',import.meta.url);const current=JSON.parse(readFileSync(file,'utf8'));
 const update=nextVersion(current,...process.argv.slice(2,4));
 if(process.argv[4]!=='--validate'){
  writeFileSync(file,JSON.stringify({...current,...update},null,2)+'\n');
  // Keep generated declarations reproducible after the next render.
  const sourceFile=new URL('./upstream-source.json',import.meta.url);
  if(existsSync(sourceFile)){const source=JSON.parse(readFileSync(sourceFile));writeFileSync(sourceFile,JSON.stringify({...source,tag:process.argv[2],build:update.build},null,2)+'\n');}
 }
}
