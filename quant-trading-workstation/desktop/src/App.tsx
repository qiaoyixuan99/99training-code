/**
 * 应用根组件 — 路由 + 布局
 */
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/dashboard';
import StockScreener from './pages/stock-screener';
import Backtest from './pages/backtest';
import StrategyEditor from './pages/strategy-editor';
import ChanTheory from './pages/chan-theory';
import MarketTiming from './pages/market-timing';
import Settings from './pages/settings';

const App: React.FC = () => {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/screener" element={<StockScreener />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/strategy-editor" element={<StrategyEditor />} />
        <Route path="/chan-theory" element={<ChanTheory />} />
        <Route path="/market-timing" element={<MarketTiming />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </AppLayout>
  );
};

export default App;
