// @vitest-environment jsdom
import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,render} from '@testing-library/react';
import TrendChart from './TrendChart';
import fixture from './trends.fixture.json';
import type {Dashboard} from './api/trends';
const mocks=vi.hoisted(()=>({construct:vi.fn(),destroy:vi.fn()}));
vi.mock('chart.js',()=>({Chart:Object.assign(vi.fn(function(_canvas:unknown,config:unknown){mocks.construct(config);return {destroy:mocks.destroy};}),{register:vi.fn()}),LineController:{},LineElement:{},PointElement:{},CategoryScale:{},LinearScale:{},Legend:{},Tooltip:{}}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
type Config={data:{labels:string[];datasets:{data:(number|null)[]}[]}};
test('comparison chart uses only the chosen calendar months and destroys its previous chart',()=>{
 const data=structuredClone(fixture) as Dashboard;
 data.filters.comparison_mode='year_over_year';data.filters.calendar_month_end=9;
 const screen=render(<TrendChart data={data}/>);
 const config=mocks.construct.mock.calls[0][0] as Config;
 expect(config.data.labels).toHaveLength(9);expect(config.data.labels[8]).toBe('September');
 expect(config.data.datasets).toHaveLength(6);
 expect(config.data.datasets.every(s=>s.data.length===9)).toBe(true);
 screen.unmount();expect(mocks.destroy).toHaveBeenCalledTimes(1);
});
test('unavailable months remain null instead of becoming zero',()=>{
 const data=structuredClone(fixture) as Dashboard;data.filters.comparison_mode='year_over_year';
 render(<TrendChart data={data}/>);
 const config=mocks.construct.mock.calls[0][0] as Config;
 expect(config.data.datasets[2].data.slice(9)).toEqual([null,null,null]);
 expect(config.data.datasets[5].data.slice(9)).toEqual([null,null,null]);
});
