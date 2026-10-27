import { afterEach,expect,test,vi } from 'vitest';
import { projectApi } from './projects';

afterEach(()=>vi.unstubAllGlobals());
test('provider retry delay is preserved for the context screen',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{"error":{"message":"Provider timed out"}}',{status:504,headers:{'Retry-After':'10'}})));
  await expect(projectApi('/test')).rejects.toMatchObject({status:504,message:'Provider timed out',retryAfterSeconds:10});
});
