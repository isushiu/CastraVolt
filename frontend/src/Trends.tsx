import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { BarChart3, RefreshCw, Sparkles, TrendingUp, CalendarDays } from 'lucide-react';
import { projectApi } from './api/projects';
import { ApiError } from './api/client';
import type { Dashboard, Explanation, TrendFilters } from './api/trends';
import { defaultFilters, queryFor, stateLabel, monthNames } from './api/trends';
import TrendChart from './TrendChart';
const number = (value: number | null) => value === null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 1 });
const period = (value: string | null) => value ? new Date(`${value}-01T12:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }) : 'Unavailable';

export default function Trends() {
    const [draft, setDraft] = useState(defaultFilters); const [active, setActive] = useState(defaultFilters);
    const [attempt, setAttempt] = useState(0); const [data, setData] = useState<Dashboard | null>(null);
    const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [filterError, setFilterError] = useState('');
    const [summary, setSummary] = useState<Explanation | null>(null); const [summaryBusy, setSummaryBusy] = useState(false); const [summaryError, setSummaryError] = useState('');
    const [retryAt, setRetryAt] = useState(0); const [clock, setClock] = useState(Date.now);
    const summaryAbort = useRef<AbortController | null>(null); const generation = useRef(0);
    useEffect(() => {
        const controller = new AbortController(); const revision = ++generation.current;
        summaryAbort.current?.abort(); setSummary(null); setSummaryBusy(false); setSummaryError(''); setRetryAt(0); setData(null); setLoading(true); setError('');
        projectApi<Dashboard>(`/trends?${queryFor(active)}`, 'GET', undefined, controller.signal).then(response => { if (revision === generation.current) { setData(response); setSummary(response.summary); } }).catch(err => { if (!controller.signal.aborted && revision === generation.current) setError(err instanceof Error ? err.message : 'Unable to load monthly trends.'); }).finally(() => { if (!controller.signal.aborted && revision === generation.current) setLoading(false); });
        return () => { controller.abort(); summaryAbort.current?.abort(); };
    }, [active, attempt]);
    useEffect(() => { if (!retryAt) return; const timer = window.setInterval(() => { setClock(Date.now()); if (Date.now() >= retryAt) window.clearInterval(timer); }, 1000); return () => window.clearInterval(timer); }, [retryAt]);
    const remaining = Math.max(0, Math.ceil((retryAt - clock) / 1000));
    const comparisons = data?.metrics.filter(metric => data.coverage.some(c => c.state === metric.state && c.year === metric.year - 1)) ?? [];
    function apply(event: FormEvent) {
        event.preventDefault(); setFilterError('');
        if (!draft.states.length || !draft.years.length) { setFilterError('Select at least one state and year.'); return; }
        if (draft.comparison_mode === 'timeline' && draft.start_month && draft.end_month && draft.start_month > draft.end_month) { setFilterError('The start month must come before the end month.'); return; }
        if (draft.calendar_month_start > draft.calendar_month_end) { setFilterError('Choose an ordered calendar-month range.'); return; }
        setActive({ ...draft });
    }
    function reset() { setFilterError(''); setDraft(defaultFilters()); setActive(defaultFilters()); }
    function toggle<T extends string | number>(values: T[], value: T): T[] { return values.includes(value) ? values.filter(v => v !== value) : [...values, value]; }
    function mode(value: TrendFilters['comparison_mode']) { setDraft({ ...draft, comparison_mode: value, start_month: null, end_month: null, calendar_month_start: 1, calendar_month_end: 12 }); }
    async function generate() {
        if (!data || summaryBusy || remaining) return;
        const controller = new AbortController(); summaryAbort.current = controller; const revision = generation.current;
        setSummaryBusy(true); setSummaryError('');
        try {
            const response = await projectApi<Explanation>('/trends/summary', 'POST', { filters: data.filters, source_version: data.source_version }, controller.signal);
            if (!controller.signal.aborted && revision === generation.current) setSummary(response);
        } catch (err) { if (!controller.signal.aborted && revision === generation.current) { setSummaryError(err instanceof Error ? err.message : 'Unable to generate an explanation.'); if (err instanceof ApiError && err.retryAfterSeconds) { setClock(Date.now()); setRetryAt(Date.now() + err.retryAfterSeconds * 1000); } } }
        finally { if (!controller.signal.aborted && revision === generation.current) setSummaryBusy(false); }
    }
    return <><div className="page-heading"><div><div className="eyebrow">REGISTRATION CONTEXT</div><h1>EV adoption trends</h1><p>Explore new electric car registrations across Kuala Lumpur and Selangor.</p></div><span className="category-pill">Monthly · 2024–2026</span></div>
        <form className="trend-filters" onSubmit={apply} aria-label="Trend filters"><div className="trend-filter-heading"><h2>Explore the data</h2><button type="button" className="text-button" onClick={reset}><RefreshCw size={14} />Reset filters</button></div><div className="trend-filter-grid">
            <fieldset><legend>States</legend>{['SELANGOR', 'W.P. KUALA LUMPUR'].map(state => <label className="trend-check" key={state}><input type="checkbox" checked={draft.states.includes(state)} onChange={() => setDraft({ ...draft, states: toggle(draft.states, state) })} />{stateLabel(state)}</label>)}</fieldset>
            <fieldset><legend>Years</legend><div className="trend-year-options">{[2024, 2025, 2026].map(year => <label className="trend-check" key={year}><input type="checkbox" checked={draft.years.includes(year)} onChange={() => setDraft({ ...draft, years: toggle(draft.years, year) })} />{year}</label>)}</div></fieldset>
            <label>Chart view<select value={draft.comparison_mode} onChange={e => mode(e.target.value as TrendFilters['comparison_mode'])}><option value="timeline">Monthly timeline</option><option value="year_over_year">Compare years</option></select></label>
            {draft.comparison_mode === 'timeline' ? <><label>From month<input type="month" min="2024-01" max="2026-12" value={draft.start_month ?? ''} onChange={e => setDraft({ ...draft, start_month: e.target.value || null })} /></label><label>To month<input type="month" min="2024-01" max="2026-12" value={draft.end_month ?? ''} onChange={e => setDraft({ ...draft, end_month: e.target.value || null })} /></label></> : <><label>From calendar month<select value={draft.calendar_month_start} onChange={e => setDraft({ ...draft, calendar_month_start: Number(e.target.value) })}>{monthNames.map((month, i) => <option value={i + 1} key={month}>{month}</option>)}</select></label><label>To calendar month<select value={draft.calendar_month_end} onChange={e => setDraft({ ...draft, calendar_month_end: Number(e.target.value) })}>{monthNames.map((month, i) => <option value={i + 1} key={month}>{month}</option>)}</select></label></>}
            <button className="button primary">Apply filters</button></div>{filterError && <p role="alert" className="auth-error">{filterError}</p>}</form>
        {loading ? <p role="status" className="trend-loading">Loading monthly registrations…</p> : error ? <section className="trend-panel"><p role="alert" className="auth-error">{error}</p><button className="button secondary" onClick={() => setAttempt(n => n + 1)}>Try again</button></section> : data && <>
            <div className="trend-active"><span>{data.filters.states.map(stateLabel).join(' + ')} · {data.filters.years.join(', ')} · {period(data.period_start)}–{period(data.period_end)}</span><span>{data.filters.comparison_mode === 'timeline' ? 'Monthly timeline' : 'Year comparison'}</span></div>
            <div className="trend-metrics"><article><span><BarChart3 size={17} />New registrations</span><strong>{number(data.total)}</strong><small>Combined selected states and covered months</small></article><article><span><TrendingUp size={17} />Monthly average</span><strong>{number(data.average_per_month)}</strong><small>Across {data.covered_months} covered calendar months</small></article><article><span><CalendarDays size={17} />Source coverage</span><strong>Jan–Sep 2026</strong><small>2024 and 2025 cover January–December</small></article></div>
            <section className="trend-panel"><div className="trend-panel-heading"><div><span className="eyebrow">MONTH BY MONTH</span><h2>New Electric Vehicle (EV) registrations</h2></div><span className="quiet-label">VEHICLES</span></div><p className="trend-note">New registrations are an adoption indicator, not the total EV fleet or neighbourhood ownership.</p>
                {data.months.length ? <><TrendChart data={data} />{data.peak && <p className="trend-note">Highest monthly state count in this view: <strong>{stateLabel(data.peak.state)} · {period(data.peak.month)} · {number(data.peak.count)} vehicles</strong>.</p>}</> : <p className="trend-empty" role="status">No covered months match these filters. Missing source coverage is not zero registrations.</p>}
                {data.filters.comparison_mode === 'year_over_year' && data.common_month_window && <button className="text-button" onClick={() => { const next = { ...active, calendar_month_start: data.common_month_window![0], calendar_month_end: data.common_month_window![1] }; setDraft(next); setActive(next); }}>Use common covered months: {monthNames[data.common_month_window[0] - 1]}–{monthNames[data.common_month_window[1] - 1]}</button>}
                <p className="trend-coverage">2024/2025: January–December. 2026: January–September only. October–December 2026 are unavailable.</p>
                {data.months.length > 0 && <details className="trend-data"><summary>View monthly data</summary><div className="trend-table-scroll"><table aria-label="Monthly new registrations"><thead><tr><th scope="col">Month</th><th scope="col">State</th><th scope="col">New registrations</th></tr></thead><tbody>{data.months.map(row => <tr key={`${row.state}:${row.month}`}><th scope="row">{period(row.month)}</th><td>{stateLabel(row.state)}</td><td>{number(row.count)}</td></tr>)}</tbody></table></div></details>}</section>
            <div className="trend-lower"><section className="trend-panel"><span className="eyebrow">MATCHING PERIODS</span><h2>Year-on-year change</h2><p className="trend-note">Compare years covered by these files. Partial years use the same available months in both years.</p><div className="trend-periods">{comparisons.map(metric => <article key={`${metric.state}:${metric.year}`}><div><strong>{stateLabel(metric.state)} · {metric.year - 1} → {metric.year}</strong><span>{period(metric.start_month)}–{period(metric.end_month)} · {number(metric.total)} vehicles</span></div><div className="trend-growth"><strong>{metric.growth.available ? `${metric.growth.percent! > 0 ? '+' : ''}${number(metric.growth.percent)}%` : 'Unavailable'}</strong><small>{metric.growth.available ? `vs ${period(metric.growth.previous_start)}–${period(metric.growth.previous_end)}` : metric.growth.reason}</small></div></article>)}</div>{!comparisons.length && <p className="trend-note">No comparable period for this selection.</p>}</section>
                <section className="trend-panel trend-summary"><span className="eyebrow">A LITTLE MORE CONTEXT</span><h2><Sparkles size={19} />Explain these trends</h2><p className="trend-note">Generate a short AI explanation of this view. Only aggregated monthly figures are sent to Groq; saved sites and individual vehicle records are excluded.</p>
                    {summary ? <><p className="trend-summary-text" role="status">{summary.text}</p><p className="trend-note">{summary.cache_hit ? 'Saved summary reused' : 'Summary saved for reuse'} · {new Date(summary.generated_at).toLocaleDateString('en-GB')} · {summary.model}</p></> : <><button className="button primary" disabled={!data.summary_enabled || !data.months.length || summaryBusy || remaining > 0} aria-busy={summaryBusy} onClick={() => void generate()}><Sparkles size={16} />{summaryBusy ? 'Generating summary…' : remaining ? `Try again in ${remaining}s` : 'Generate summary'}</button>{!data.summary_enabled && <p className="trend-note">AI explanations are not configured. Charts and calculated statistics are available.</p>}</>}
                    {summaryError && <p role="alert" className="auth-error">{summaryError}</p>}<p className="trend-note">AI explanations may contain errors. Use the chart and calculated figures to verify them. Identical filters reuse a saved summary.</p></section></div>
            <section className="trend-source"><h3>About these figures</h3><p>Filtered source files: fully electric vehicle in Selangor and W.P. Kuala Lumpur. Rakan Niaga, other states and vehicle types are excluded. Figures are registration records, not total EV ownership or charging demand.</p><details><summary>Source files and version</summary><p>Dataset version: {data.source_version}</p><ul>{data.sources.map(source => <li key={source.filename}>{source.filename} · {number(source.accepted)} records · SHA256 {source.sha256}</li>)}</ul></details></section>
        </>}
    </>;
}
