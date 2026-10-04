import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import createPlot from 'react-plotly.js/factory'
import Plotly from 'plotly.js/dist/plotly-basic.min.js'
import type { Layout, Shape } from 'plotly.js'
import type { Trace } from '../../types'
import { number } from '../../format'

const Plot = createPlot(Plotly)

export default function TraceChart({ run, start, end }: { run: Trace; start: number | null; end: number | null }) {
  const [mode, setMode] = useState<'zoom' | 'pan'>('zoom')
  const [reset, setReset] = useState(0)
  const [failed, setFailed] = useState(false)
  const container = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  useLayoutEffect(() => {
    const element = container.current!
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize(current => current.width === width && current.height === height ? current : { width, height })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  const data = useMemo(() => [{
    x: run.points.map(p => p[0]), y: run.points.map(p => p[1]), type: 'scatter' as const, mode: 'lines' as const,
    line: { color: '#2457c5', width: 2, shape: 'linear' as const, simplify: false },
    hovertemplate: '%{x:.6g} min<br>%{y:.6g} AU<extra></extra>',
  }], [run.points])
  const shapes: Partial<Shape>[] = start !== null && end !== null ? [
    { type: 'rect', x0: start, x1: end, y0: 0, y1: 1, yref: 'paper', fillcolor: 'rgba(36,87,197,0.08)', line: { width: 0 }, layer: 'below' },
    ...[start, end].map(value => ({ type: 'line' as const, x0: value, x1: value, y0: 0, y1: 1, yref: 'paper' as const, line: { color: '#617baf', width: 1, dash: 'dot' as const } })),
  ] : []
  const layout: Partial<Layout> = {
    autosize: false, width: size.width, height: size.height,
    margin: { t: 25, r: 24, b: 62, l: 64 }, showlegend: false,
    paper_bgcolor: '#ffffff', plot_bgcolor: '#ffffff',
    font: { family: 'Segoe UI, system-ui, sans-serif', size: 12, color: '#555d6b' },
    xaxis: { title: { text: 'Time (min)', standoff: 18 }, gridcolor: '#eceef2', zeroline: false },
    yaxis: { title: { text: 'Signal (AU)', standoff: 16 }, gridcolor: '#eceef2', zeroline: false, rangemode: 'tozero' },
    shapes, dragmode: mode, hovermode: 'closest', uirevision: `${run.id}-${reset}`,
  }
  return <section className="chart-region" aria-label="Trace chart">
    <div className="chart-tools" role="group" aria-label="Chart viewport">
      <button aria-pressed={mode === 'zoom'} onClick={() => setMode('zoom')}>Zoom</button>
      <button aria-pressed={mode === 'pan'} onClick={() => setMode('pan')}>Pan</button>
      <button onClick={() => setReset(value => value + 1)}>Reset zoom</button>
    </div>
    <div ref={container} className="plot" role="img" aria-label={`${run.point_count} measured points. Time in minutes; signal in arbitrary units. Use Data for a numerical table.`}>
      {failed ? <p role="alert" className="error">Chart unavailable. Use the boundary fields and Data table.</p> :
        size.width > 0 &&
        <Plot data={data} layout={layout} config={{ displayModeBar: false, displaylogo: false, responsive: true, scrollZoom: false, doubleClick: 'reset' }}
          style={{ width: '100%', height: '100%' }} onError={() => setFailed(true)} />}
    </div>
    <p className="chart-caption">Total integration window: entire trace, {number(run.time_min)}–{number(run.time_max)} min.</p>
  </section>
}
