<template>
  <div class="app" :class="{ 'is-collapsed': sidebarCollapsed }">
    <aside class="sidebar" id="app-sidebar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path v-for="d in brandIcon" :key="d" :d="d" />
          </svg>
        </span>
        <span class="brand-text">
          <span class="brand-name">{{ t('nav.companyName') }}</span>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </span>
      </div>

      <nav class="sidebar-nav" :aria-label="t('nav.mainNavigation')">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: $route.path === item.path }"
          :aria-label="t(item.labelKey)"
          :title="t(item.labelKey)"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in item.icon" :key="d" :d="d" />
          </svg>
          <span class="nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <button
        type="button"
        class="collapse-toggle"
        :aria-expanded="String(!sidebarCollapsed)"
        aria-controls="app-sidebar"
        :aria-label="sidebarCollapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="sidebarCollapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="toggleSidebar"
      >
        <svg class="nav-icon toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M11 17l-5-5 5-5" />
          <path d="M18 17l-5-5 5-5" />
        </svg>
        <span class="nav-label">{{ t('nav.collapseSidebar') }}</span>
      </button>
    </aside>

    <div class="main-column">
      <header class="topbar">
        <div class="topbar-actions">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
        <div class="topbar-filters">
          <FilterBar />
        </div>
      </header>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

const SIDEBAR_KEY = 'sidebar-collapsed'

// Sidebar navigation. Each item: route path, i18n label key, and SVG path data
// (24x24 stroke icon). Add new entries here to extend the nav.
const navItems = [
  { path: '/', labelKey: 'nav.overview', icon: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M14 14h7v7h-7z', 'M3 14h7v7H3z'] },
  { path: '/inventory', labelKey: 'nav.inventory', icon: ['M21 8l-9-5-9 5v8l9 5 9-5V8z', 'M3 8l9 5 9-5', 'M12 13v8'] },
  { path: '/orders', labelKey: 'nav.orders', icon: ['M9 3h6a1 1 0 011 1v1H8V4a1 1 0 011-1z', 'M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V7a2 2 0 00-2-2h-2', 'M8 11h8', 'M8 15h5'] },
  { path: '/spending', labelKey: 'nav.finance', icon: ['M12 2v20', 'M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6'] },
  { path: '/demand', labelKey: 'nav.demandForecast', icon: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'] },
  { path: '/restocking', labelKey: 'nav.restocking', icon: ['M21 12a9 9 0 01-15.5 6.2', 'M3 12a9 9 0 0115.5-6.2', 'M18.5 2v4h-4', 'M5.5 22v-4h4'] },
  { path: '/reports', labelKey: 'nav.reports', icon: ['M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z', 'M14 3v5h5', 'M9 13h6', 'M9 17h6'] },
  { path: '/backlog', labelKey: 'nav.backlog', icon: ['M12 3a9 9 0 100 18 9 9 0 000-18z', 'M12 7v5l3 2'] }
]

const brandIcon = ['M21 8l-9-5-9 5v8l9 5 9-5V8z', 'M3 8l9 5 9-5', 'M12 13v8']

const readCollapsed = () => {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === 'true'
  } catch (e) {
    return false
  }
}

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])
    // User's saved sidebar choice. Below 900px CSS forces icons-only regardless.
    const sidebarCollapsed = ref(readCollapsed())

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      try {
        localStorage.setItem(SIDEBAR_KEY, String(sidebarCollapsed.value))
      } catch (e) {
        // Storage unavailable: choice just isn't remembered
      }
    }

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      brandIcon,
      sidebarCollapsed,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* Design tokens (slate/gray system with blue accent) */
:root {
  --color-canvas: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;
  --color-text-body: #334155;
  --color-text-muted: #64748b;
  --color-accent: #2563eb;
  --color-accent-soft: #eff6ff;
  --color-success: #059669;
  --color-warning: #ea580c;
  --color-danger: #dc2626;

  --radius-card: 12px;
  --radius-control: 8px;
  --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
  --focus-ring: 0 0 0 2px var(--color-surface), 0 0 0 4px var(--color-accent);

  --sidebar-width: 15rem;
  --sidebar-width-collapsed: 4.5rem;
  --topbar-pad: 0.75rem 1.5rem;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-canvas);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* ---------- App shell ---------- */
.app {
  --sidebar-w: var(--sidebar-width);
  min-height: 100vh;
}

.app.is-collapsed {
  --sidebar-w: var(--sidebar-width-collapsed);
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-w);
  z-index: 110;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 0.75rem;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.2s ease;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0.5rem 1rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  min-height: 3.5rem;
}

.brand-mark {
  flex: 0 0 2.25rem;
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-control);
  background: var(--color-accent);
  color: #ffffff;
}

.brand-mark svg {
  width: 1.25rem;
  height: 1.25rem;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-size: 0.938rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.3;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.nav-link,
.collapse-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  min-height: 2.5rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-muted);
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-link:hover,
.collapse-toggle:hover {
  color: var(--color-text);
  background: var(--color-surface-muted);
}

.nav-link:focus-visible,
.collapse-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Active item: tinted background, bold weight and a left bar (not color alone) */
.nav-link.active {
  color: var(--color-accent);
  background: var(--color-accent-soft);
  font-weight: 700;
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: -0.75rem;
  top: 0.5rem;
  bottom: 0.5rem;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--color-accent);
}

.nav-icon {
  flex: 0 0 1.25rem;
  width: 1.25rem;
  height: 1.25rem;
}

.collapse-toggle {
  margin-top: auto;
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 var(--radius-control) var(--radius-control);
  padding-top: 0.75rem;
  min-height: 3rem;
}

.toggle-icon {
  transition: transform 0.2s ease;
}

.app.is-collapsed .toggle-icon {
  transform: rotate(180deg);
}

.main-column {
  margin-left: var(--sidebar-w);
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.2s ease;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem 1rem;
  padding: var(--topbar-pad);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.topbar-filters {
  order: 2;
  flex: 1 1 100%;
  min-width: 0;
}

.topbar-actions {
  order: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* Wide screens: filters and actions share a single row */
@media (min-width: 1500px) {
  .topbar {
    flex-wrap: nowrap;
  }

  .topbar-filters {
    order: 0;
    flex: 1 1 auto;
  }

  .topbar-actions {
    order: 1;
  }
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: 1600px;
  min-width: 0;
  margin: 0 auto;
  padding: 1.5rem;
}

/* Sidebar is icons-only below 900px, whatever the saved choice */
.app.is-collapsed .brand-text,
.app.is-collapsed .nav-label {
  display: none;
}

.app.is-collapsed .brand,
.app.is-collapsed .nav-link,
.app.is-collapsed .collapse-toggle {
  justify-content: center;
}

.app.is-collapsed .nav-link,
.app.is-collapsed .collapse-toggle {
  padding-left: 0;
  padding-right: 0;
}

.app.is-collapsed .brand {
  padding-left: 0;
  padding-right: 0;
}

@media (max-width: 899px) {
  .app {
    --sidebar-w: var(--sidebar-width-collapsed);
  }

  .brand-text,
  .nav-label {
    display: none;
  }

  .brand,
  .nav-link {
    justify-content: center;
  }

  .nav-link {
    padding-left: 0;
    padding-right: 0;
  }

  .brand {
    padding-left: 0;
    padding-right: 0;
  }

  .collapse-toggle {
    display: none;
  }

  .topbar {
    position: static;
    padding: 0.75rem 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  .topbar .profile-name {
    display: none;
  }
}

@media (max-width: 480px) {
  :root {
    --sidebar-width-collapsed: 3.5rem;
  }

  .sidebar {
    padding-left: 0.375rem;
    padding-right: 0.375rem;
  }

  .nav-link.active::before {
    left: -0.375rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .main-column,
  .toggle-icon,
  .nav-link,
  .collapse-toggle {
    transition: none;
  }
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.625rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--color-surface);
  padding: 1.25rem;
  border-radius: var(--radius-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: 1.25rem;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

/* Tables scroll inside their own container, never the page */
.table-container {
  overflow-x: auto;
  max-width: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
