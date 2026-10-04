import { Component } from 'react'
import type { ReactNode } from 'react'

export default class ChartBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed
      ? <div className="chart-loading error" role="alert">Chart unavailable. Use the boundary fields and Data table.</div>
      : this.props.children
  }
}
