import {useEffect,useRef} from 'react';
import {Chart,LineController,LineElement,PointElement,CategoryScale,LinearScale,Legend,Tooltip} from 'chart.js';
import type {ChartDataset} from 'chart.js';
import type {Dashboard} from './api/trends';
import {stateLabel,monthNames} from './api/trends';
Chart.register(LineController,LineElement,PointElement,CategoryScale,LinearScale,Legend,Tooltip);

export default function TrendChart({data}:{data:Dashboard}){
 const canvas=useRef<HTMLCanvasElement>(null);
 useEffect(()=>{
  if(!canvas.current)return;
  const comparison=data.filters.comparison_mode==='year_over_year';
  const months=[...new Set(data.months.map(r=>r.month))].sort();
  const calendarMonths=monthNames.map((name,index)=>({name,number:index+1})).filter(m=>m.number>=data.filters.calendar_month_start&&m.number<=data.filters.calendar_month_end);
  const labels=comparison?calendarMonths.map(m=>m.name):months.map(m=>new Date(`${m}-01T12:00:00Z`).toLocaleDateString('en-GB',{month:'short',year:'numeric',timeZone:'UTC'}));
  const colours=['#6844D8','#138B84','#A15AB0','#3871B5','#A67719','#CD6476'];
  const series:ChartDataset<'line'>[]=[];
  for(const state of data.filters.states){
   const years=comparison?data.filters.years:[null];
   for(const year of years){
    const points=comparison?calendarMonths.map(m=>data.months.find(r=>r.state===state&&r.month===`${year}-${String(m.number).padStart(2,'0')}`)?.count??null):months.map(m=>data.months.find(r=>r.state===state&&r.month===m)?.count??null);
    series.push({label:`${stateLabel(state)}${year?` · ${year}`:''}`,data:points,borderColor:colours[series.length%colours.length],backgroundColor:colours[series.length%colours.length],borderWidth:2,pointRadius:2,pointHoverRadius:5,tension:.2,spanGaps:false,borderDash:year===2025?[6,3]:year===2024?[2,2]:undefined});
   }
  }
  const chart=new Chart(canvas.current,{type:'line',data:{labels,datasets:series},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:16,usePointStyle:true,padding:20,color:'#655B76'}},tooltip:{callbacks:{label:context=>`${context.dataset.label}: ${context.parsed.y?.toLocaleString('en-GB')} vehicles`}}},scales:{x:{grid:{display:false},ticks:{maxRotation:45,color:'#81748D',maxTicksLimit:12},title:{display:true,text:'Registration month'}},y:{beginAtZero:true,ticks:{precision:0,color:'#81748D'},grid:{color:'#F0EDF5'},title:{display:true,text:'New registrations (vehicles)'}}}}});
  return()=>chart.destroy();
 },[data]);
 return <div className="trend-chart"><canvas ref={canvas} role="img" aria-label="Monthly new electric motokar registrations by state. Exact counts are available in the monthly data table below."/></div>;
}
