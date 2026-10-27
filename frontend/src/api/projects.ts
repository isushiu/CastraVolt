import { ApiError } from './client';
import type { components } from './schema';

export type Project = components['schemas']['ProjectResult'];
export type Site = components['schemas']['SiteResult'];
export type Prediction = components['schemas']['PredictionResult'];
export type SiteInput = components['schemas']['SiteInput'];

export async function projectApi<T>(path: string, method='GET', data?: unknown, signal?: AbortSignal): Promise<T> {
  const headers: Record<string,string>={};
  if(method!=='GET') {
    const csrfResponse=await fetch('/api/v1/auth/csrf',{credentials:'include',cache:'no-store',signal});
    if(!csrfResponse.ok) throw new ApiError('Unable to start this request. Please retry.',csrfResponse.status);
    headers['X-CSRF-Token']=(await csrfResponse.json()).csrf_token;
    headers['Content-Type']='application/json';
  }
  const response=await fetch('/api/v1'+path,{method,credentials:'include',cache:'no-store',headers,
    body:data===undefined?undefined:JSON.stringify(data),signal});
  if(!response.ok) {
    if(response.status===401) window.dispatchEvent(new Event('castravolt:unauthenticated'));
    const body=await response.json().catch(()=>null);
    throw new ApiError(body?.error?.message??'Unable to complete the request. Please retry.',response.status);
  }
  if(response.status===204) return undefined as T;
  return response.json();
}
