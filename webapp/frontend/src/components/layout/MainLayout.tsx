import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Project } from '../../types';

export const MainLayout: React.FC = () => {
  const [currentProject, setCurrentProject] = useState<Project | null>(null);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-page text-text-primary">
      {/* Black Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <Topbar currentProject={currentProject} onSelectProject={setCurrentProject} />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-page">
          <Outlet context={{ currentProject }} />
        </main>
      </div>
    </div>
  );
};

