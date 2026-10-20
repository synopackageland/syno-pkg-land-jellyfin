import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {nextVersion} from '../version.mjs';
test('upstream two-part version is preserved and same-release builds increase',()=>{
 assert.deepEqual(nextVersion({version:'12.2',build:1},'v12.2','2'),{version:'12.2',build:2});
 assert.throws(()=>nextVersion({version:'12.2',build:1},'v12.2','1'));
});
test('a new upstream release starts at build 0001',()=>{
 assert.deepEqual(nextVersion({version:'12.2',build:4},'v12.3','1'),{version:'12.3',build:1});
 assert.throws(()=>nextVersion({version:'12.2',build:4},'v12.3','5'));
 assert.throws(()=>nextVersion({version:'12.2',build:4},'v12.1','1'));
});
test('pre-release tags and out-of-range builds are rejected',()=>{
 for(const tag of ['v12.2-rc1','v12','v012.2','v12.2;touch /tmp/x'])assert.throws(()=>nextVersion({version:'12.1',build:1},tag,'1'));
 for(const build of ['0','10000','-1','x'])assert.throws(()=>nextVersion({version:'12.1',build:1},'v12.2',build));
});
