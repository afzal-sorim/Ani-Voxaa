import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import useThemeStore from '../store/useThemeStore';
import useChatStore from '../store/useChatStore';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadTheme     = useThemeStore((s) => s.loadTheme);
  const loadFromCache = useChatStore((s) => s.loadFromCache);
  const newChat       = useChatStore((s) => s.newChat);

  useEffect(() => {
    loadTheme();
    loadFromCache();
  }, [loadTheme, loadFromCache]);

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);
  const closeSidebar  = () => setSidebarOpen(false);

  return (
    <div
      className="flex w-full h-screen overflow-hidden bg-[var(--bg)] transition-colors duration-250"
      id="app-root"
    >
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      <div
        className="flex flex-col h-screen min-w-0 relative pt-16 transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]"
        style={{
          flex: 1,
          marginLeft: sidebarOpen ? '240px' : '0px',
          width: sidebarOpen ? 'calc(100% - 240px)' : '100%'
        }}
        id="main-content"
      >
        <Header onToggleSidebar={toggleSidebar} onCloseSidebar={closeSidebar} />
        <ChatWindow />
      </div>
    </div>
  );
}
