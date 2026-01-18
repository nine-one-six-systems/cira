/**
 * Tabs Component
 *
 * A tabbed interface for organizing content.
 */

import { useState, useCallback, useId } from 'react';

export interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  /** Tab definitions */
  tabs: Tab[];
  /** Initially selected tab ID */
  defaultTab?: string;
  /** Change handler */
  onChange?: (tabId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Tabs component for organizing content into tabbed sections.
 *
 * @example
 * ```tsx
 * <Tabs
 *   tabs={[
 *     { id: 'summary', label: 'Summary', content: <SummaryTab /> },
 *     { id: 'entities', label: 'Entities', content: <EntitiesTab /> },
 *     { id: 'pages', label: 'Pages', content: <PagesTab /> },
 *   ]}
 *   defaultTab="summary"
 *   onChange={(tabId) => console.log('Tab changed:', tabId)}
 * />
 * ```
 */
export function Tabs({
  tabs,
  defaultTab,
  onChange,
  className = '',
}: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);
  const baseId = useId();

  const handleTabClick = useCallback(
    (tabId: string) => {
      setActiveTab(tabId);
      onChange?.(tabId);
    },
    [onChange]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const enabledTabs = tabs.filter((t) => !t.disabled);
      const currentIndex = enabledTabs.findIndex((t) => t.id === activeTab);

      let nextIndex = currentIndex;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          nextIndex = currentIndex > 0 ? currentIndex - 1 : enabledTabs.length - 1;
          break;
        case 'ArrowRight':
          e.preventDefault();
          nextIndex = currentIndex < enabledTabs.length - 1 ? currentIndex + 1 : 0;
          break;
        case 'Home':
          e.preventDefault();
          nextIndex = 0;
          break;
        case 'End':
          e.preventDefault();
          nextIndex = enabledTabs.length - 1;
          break;
        default:
          return;
      }

      const nextTab = enabledTabs[nextIndex];
      if (nextTab) {
        setActiveTab(nextTab.id);
        onChange?.(nextTab.id);
        // Focus the tab button
        const tabElement = document.getElementById(`${baseId}-tab-${nextTab.id}`);
        tabElement?.focus();
      }
    },
    [tabs, activeTab, onChange, baseId]
  );

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div className={className}>
      {/* Tab List */}
      <div
        role="tablist"
        aria-label="Content tabs"
        className="flex border-b border-neutral-200"
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              id={`${baseId}-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`${baseId}-panel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              disabled={tab.disabled}
              onClick={() => handleTabClick(tab.id)}
              onKeyDown={handleKeyDown}
              className={`
                px-4 py-3
                text-sm font-medium
                border-b-2 -mb-px
                transition-colors duration-150
                focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500
                ${isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                }
                ${tab.disabled ? 'opacity-50 cursor-not-allowed' : ''}
              `.trim().replace(/\s+/g, ' ')}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <div
            key={tab.id}
            id={`${baseId}-panel-${tab.id}`}
            role="tabpanel"
            aria-labelledby={`${baseId}-tab-${tab.id}`}
            hidden={!isActive}
            tabIndex={0}
            className="py-4 focus:outline-none"
          >
            {isActive && activeContent}
          </div>
        );
      })}
    </div>
  );
}

export default Tabs;
