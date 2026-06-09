/**
 * K线图表组件 — 基于 lightweight-charts (TradingView)
 * 支持：日线/周线/月线/分时 | 成交量 | 缠论标注叠加层
 */
import React, { useEffect, useRef } from 'react';
import {
  createChart, IChartApi, ISeriesApi, CandlestickData, LineData,
  HistogramData, Time, LineStyle,
} from 'lightweight-charts';

interface KLineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface FractalOverlay {
  index: number;
  date: string;
  type: 'top' | 'bottom';
  price: number;
  level?: string;
}

interface StrokeOverlay {
  start_index: number;
  end_index: number;
  start_date: string;
  end_date: string;
  direction: 'up' | 'down';
  start_price: number;
  end_price: number;
}

interface CenterOverlay {
  zg: number;
  zd: number;
  start_index: number;
  end_index: number;
  start_date: string;
  end_date: string;
}

interface BuySellOverlay {
  index: number;
  date: string;
  type: string;
  price: number;
}

interface KLineChartProps {
  data: KLineData[];
  height?: number;
  showVolume?: boolean;
  symbol?: string;
  period?: string;
  // 缠论叠加
  fractals?: FractalOverlay[];
  strokes?: StrokeOverlay[];
  centers?: CenterOverlay[];
  buyPoints?: BuySellOverlay[];
  sellPoints?: BuySellOverlay[];
}

const KLineChart: React.FC<KLineChartProps> = ({
  data,
  height = 500,
  showVolume = true,
  symbol = '',
  period = '1d',
  fractals = [],
  strokes = [],
  centers = [],
  buyPoints = [],
  sellPoints = [],
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const isIntraday = ['5m', '15m', '30m', '60m', '1m'].includes(period);
    const volumeHeight = showVolume ? Math.floor(height * 0.2) : 0;
    const mainHeight = height - volumeHeight;

    // ── 创建图表 ──
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0d1117' },
        textColor: '#8b949e',
      },
      grid: {
        vertLines: { color: '#1c2129' },
        horzLines: { color: '#1c2129' },
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#30363d',
          style: 2,
          labelBackgroundColor: '#30363d',
        },
        horzLine: {
          color: '#30363d',
          style: 2,
          labelBackgroundColor: '#30363d',
        },
      },
      rightPriceScale: {
        borderColor: '#30363d',
        scaleMargins: showVolume ? { top: 0.05, bottom: 0.25 } : { top: 0.05, bottom: 0.05 },
      },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: mainHeight,
    });

    // ── K线系列 ──
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef5350',
      downColor: '#26a69a',
      borderUpColor: '#ef5350',
      borderDownColor: '#26a69a',
      wickUpColor: '#ef5350',
      wickDownColor: '#26a69a',
    });

    // 时间格式转换
    const formatTime = (d: KLineData): Time => {
      if (isIntraday) {
        // 分时数据：日期+时间格式 "2024-01-15 09:30"
        const dateStr = d.date;
        if (dateStr.includes(' ')) {
          return dateStr as Time;
        }
        return dateStr as Time;
      }
      // 日线数据
      return (d.date.length > 10 ? d.date.slice(0, 10) : d.date) as Time;
    };

    const candleData = data.map((d) => ({
      time: formatTime(d),
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    } as CandlestickData));

    candleSeries.setData(candleData);

    // ── 缠论标注层：合并分型标记 + 买卖点标记 ──
    const allMarkers: any[] = [];

    // 分型标记（顶分型用箭头向下，底分型用箭头向上）
    if (fractals.length > 0) {
      fractals.forEach(f => {
        if (f.index < data.length) {
          const isBuy = buyPoints.some(bp => bp.index === f.index);
          const isSell = sellPoints.some(sp => sp.index === f.index);
          // 如果该位置同时是买卖点，不重复标记（买卖点优先级更高）
          if (!isBuy && !isSell) {
            allMarkers.push({
              time: formatTime(data[f.index]),
              position: f.type === 'top' ? 'aboveBar' : 'belowBar',
              color: f.level === 'major'
                ? (f.type === 'top' ? '#ff6666' : '#66ff66')
                : f.level === 'medium'
                ? (f.type === 'top' ? '#ff9999' : '#99ff99')
                : 'rgba(150,150,150,0.5)',
              shape: f.type === 'top' ? 'arrowDown' : 'arrowUp',
              text: f.level === 'major' ? (f.type === 'top' ? '顶' : '底') : '',
              size: f.level === 'major' ? 3 : f.level === 'medium' ? 2 : 1,
            });
          }
        }
      });
    }

    // 买卖点标记
    buyPoints.forEach(bp => {
      if (bp.index < data.length) {
        allMarkers.push({
          time: formatTime(data[bp.index]),
          position: 'belowBar',
          color: '#00ff00',
          shape: 'arrowUp',
          text: bp.type.replace('buy', '买'),
          size: 3,
        });
      }
    });

    sellPoints.forEach(sp => {
      if (sp.index < data.length) {
        allMarkers.push({
          time: formatTime(data[sp.index]),
          position: 'aboveBar',
          color: '#ff0000',
          shape: 'arrowDown',
          text: sp.type.replace('sell', '卖'),
          size: 3,
        });
      }
    });

    if (allMarkers.length > 0) {
      candleSeries.setMarkers(allMarkers);
    }

    // ── 中枢区域（半透明矩形）──
    if (centers.length > 0 && data.length > 0) {
      centers.forEach((c, ci) => {
        if (c.start_index < data.length) {
          const startTime = formatTime(data[Math.min(c.start_index, data.length - 1)]);
          const endTime = formatTime(data[Math.min(c.end_index, data.length - 1)]);

          // 使用背景色标记中枢区间
          const color = ci % 2 === 0 ? 'rgba(255, 215, 0, 0.08)' : 'rgba(100, 149, 237, 0.08)';
          const borderColor = ci % 2 === 0 ? 'rgba(255, 215, 0, 0.3)' : 'rgba(100, 149, 237, 0.3)';

          // 中枢上轨线
          const zgLine = chart.addLineSeries({
            color: borderColor,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          zgLine.setData([
            { time: startTime, value: c.zg },
            { time: endTime, value: c.zg },
          ]);

          // 中枢下轨线
          const zdLine = chart.addLineSeries({
            color: borderColor,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          zdLine.setData([
            { time: startTime, value: c.zd },
            { time: endTime, value: c.zd },
          ]);
        }
      });
    }

    // 上升笔（绿色虚线）
    const upStrokes = strokes.filter(s => s.direction === 'up');
    if (upStrokes.length > 0) {
      upStrokes.forEach(s => {
        if (s.start_index < data.length && s.end_index < data.length) {
          const line = chart.addLineSeries({
            color: 'rgba(38, 166, 154, 0.5)',
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          line.setData([
            { time: formatTime(data[s.start_index]), value: s.start_price },
            { time: formatTime(data[s.end_index]), value: s.end_price },
          ]);
        }
      });
    }

    // 下降笔（红色虚线）
    const downStrokes = strokes.filter(s => s.direction === 'down');
    if (downStrokes.length > 0) {
      downStrokes.forEach(s => {
        if (s.start_index < data.length && s.end_index < data.length) {
          const line = chart.addLineSeries({
            color: 'rgba(239, 83, 80, 0.5)',
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          line.setData([
            { time: formatTime(data[s.start_index]), value: s.start_price },
            { time: formatTime(data[s.end_index]), value: s.end_price },
          ]);
        }
      });
    }

    // ── 成交量 ──
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const volumeData = data.map((d, i) => {
        const prevClose = i > 0 ? data[i - 1].close : d.open;
        return {
          time: formatTime(d),
          value: d.volume,
          color: d.close >= prevClose ? 'rgba(239, 83, 80, 0.5)' : 'rgba(38, 166, 154, 0.5)',
        };
      });

      volumeSeries.setData(volumeData);
    }

    chartRef.current = chart;
    chart.timeScale().fitContent();

    // 响应式
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [data, height, showVolume, period,
    // 缠论overlay更新时也需要重建（简单方案）
    JSON.stringify(fractals.map(f => `${f.index}:${f.type}:${f.level}`)),
    JSON.stringify(strokes.map(s => `${s.start_index}:${s.end_index}`)),
    JSON.stringify(centers.map(c => `${c.start_index}:${c.end_index}`)),
    JSON.stringify(buyPoints.map(p => `${p.index}:${p.type}`)),
    JSON.stringify(sellPoints.map(p => `${p.index}:${p.type}`)),
  ]);

  return (
    <div>
      {symbol && (
        <div style={{ marginBottom: 8, fontSize: 16, fontWeight: 600, color: '#e6edf3' }}>
          {symbol}
        </div>
      )}
      <div
        ref={chartContainerRef}
        style={{
          width: '100%',
          height: height,
          borderRadius: 8,
          overflow: 'hidden',
          border: '1px solid #30363d',
        }}
      />
    </div>
  );
};

export default KLineChart;
