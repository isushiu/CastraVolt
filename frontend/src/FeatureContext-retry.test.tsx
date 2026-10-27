// @vitest-environment jsdom
import { afterEach,expect,test,vi } from 'vitest';
import { act,cleanup,render,screen } from '@testing-library/react';
import FeatureContext from './FeatureContext';

afterEach(()=>{cleanup();vi.useRealTimers();});
test('retry countdown prevents early requests and enables retry when it expires',()=>{
  vi.useFakeTimers();vi.setSystemTime(new Date('2026-10-27T00:00:00Z'));
  render(<FeatureContext context={null} busy={false} error="Provider timed out" ready onPrepare={()=>{}} retryAt={Date.now()+5000}/>);
  expect((screen.getByRole('button',{name:'Try again in 5s'}) as HTMLButtonElement).disabled).toBe(true);
  act(()=>vi.advanceTimersByTime(5000));
  expect((screen.getByRole('button',{name:'Prepare site context'}) as HTMLButtonElement).disabled).toBe(false);
});
