export type TrendFilters={states:string[];years:number[];comparison_mode:'timeline'|'year_over_year';start_month:string|null;end_month:string|null;calendar_month_start:number;calendar_month_end:number};
export type MonthRow={state:string;month:string;count:number};
export type Explanation={text:string;model:string;prompt_version:string;source_version:string;generated_at:string;cache_hit:boolean};
export type Growth={available:boolean;percent:number|null;previous_total:number|null;previous_start:string;previous_end:string;reason:string|null};
export type PeriodMetric={state:string;year:number;start_month:string;end_month:string;total:number;covered_months:number;average_per_month:number;growth:Growth};
export type Dashboard={source_version:string;scope:{fuel:string;type:string;states:string[];excluded:string};sources:{filename:string;sha256:string;accepted:number;excluded:number}[];coverage:{state:string;year:number;start_month:string;end_month:string}[];filters:TrendFilters;months:MonthRow[];total:number|null;covered_months:number;average_per_month:number|null;period_start:string|null;period_end:string|null;common_month_window:number[]|null;metrics:PeriodMetric[];peak:MonthRow|null;summary_enabled:boolean;summary:Explanation|null;metric_label:string};
export const defaultFilters=():TrendFilters=>({states:['SELANGOR','W.P. KUALA LUMPUR'],years:[2024,2025,2026],comparison_mode:'timeline',start_month:null,end_month:null,calendar_month_start:1,calendar_month_end:12});
export const stateLabel=(state:string)=>state==='SELANGOR'?'Selangor':'Kuala Lumpur';
export const monthNames=['January','February','March','April','May','June','July','August','September','October','November','December'];
export function queryFor(filters:TrendFilters){
 const params=new URLSearchParams({states:filters.states.join(','),years:filters.years.join(','),comparison_mode:filters.comparison_mode});
 if(filters.comparison_mode==='timeline'){
  if(filters.start_month)params.set('start_month',filters.start_month);
  if(filters.end_month)params.set('end_month',filters.end_month);
 }else{params.set('calendar_month_start',String(filters.calendar_month_start));params.set('calendar_month_end',String(filters.calendar_month_end));}
 return params.toString();
}
