/**
 * Zustand 全局状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ── 类型定义 ──

interface WatchlistItem {
  symbol: string;
  name: string;
  group: string;
}

interface UserSettings {
  dataSource: 'akshare' | 'tushare' | 'baostock';
  strategyDir: string;
  defaultPeriod: string;
  theme: 'dark' | 'light';
}

interface AppState {
  // 当前选中的股票
  activeSymbol: string | null;
  setActiveSymbol: (symbol: string) => void;

  // 当前K线周期
  activePeriod: string;
  setActivePeriod: (period: string) => void;

  // 自选股
  watchlist: WatchlistItem[];
  addToWatchlist: (item: WatchlistItem) => void;
  removeFromWatchlist: (symbol: string) => void;

  // 用户设置
  settings: UserSettings;
  updateSettings: (settings: Partial<UserSettings>) => void;

  // 回测状态
  backtestRunning: boolean;
  setBacktestRunning: (running: boolean) => void;
  backtestResult: any | null;
  setBacktestResult: (result: any) => void;
}

// ── Store ──

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      // 当前股票
      activeSymbol: null,
      setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),

      // K线周期
      activePeriod: '1d',
      setActivePeriod: (period) => set({ activePeriod: period }),

      // 自选股
      watchlist: [],
      addToWatchlist: (item) =>
        set((state) => ({
          watchlist: [...state.watchlist.filter((w) => w.symbol !== item.symbol), item],
        })),
      removeFromWatchlist: (symbol) =>
        set((state) => ({
          watchlist: state.watchlist.filter((w) => w.symbol !== symbol),
        })),

      // 设置
      settings: {
        dataSource: 'akshare',
        strategyDir: '',
        defaultPeriod: '1d',
        theme: 'dark',
      },
      updateSettings: (partial) =>
        set((state) => ({
          settings: { ...state.settings, ...partial },
        })),

      // 回测
      backtestRunning: false,
      setBacktestRunning: (running) => set({ backtestRunning: running }),
      backtestResult: null,
      setBacktestResult: (result) => set({ backtestResult: result }),
    }),
    {
      name: 'quant-trading-storage',
      partialize: (state) => ({
        watchlist: state.watchlist,
        settings: state.settings,
        activePeriod: state.activePeriod,
      }),
    }
  )
);
