export type ChartType = "bar" | "line"

export type ChartDataset = {
  label: string
  data: number[]
  backgroundColor: string
  borderColor?: string
  fill?: boolean
}

export type ChartConfig = {
  type: ChartType
  data: {
    labels: string[]
    datasets: ChartDataset[]
  }
  options?: {
    responsive?: boolean
    maintainAspectRatio?: boolean
    scales?: {
      y?: {
        beginAtZero?: boolean
        grace?: string
        ticks?: {
          precision?: number
        }
      }
    }
  }
}

export type ChartInstance = {
  destroy(): void
}

export type ChartConstructor = new (canvas: HTMLCanvasElement, config: ChartConfig) => ChartInstance

declare global {
  interface Window {
    Chart?: ChartConstructor
  }
}

export {}
