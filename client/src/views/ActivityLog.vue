<template>
  <div class="activity-log">
    <div class="page-header header-row">
      <div>
        <h2>{{ t('activity.title') }}</h2>
        <p>{{ t('activity.description') }}</p>
      </div>
      <button type="button" class="refresh-button" :disabled="loading" @click="loadEntries">
        {{ t('activity.refresh') }}
      </button>
    </div>

    <div v-if="loading && entries.length === 0" class="loading" role="status">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error" role="alert">{{ error }}</div>
    <div v-else-if="entries.length === 0" class="card empty-state">{{ t('activity.empty') }}</div>
    <div v-else class="card">
      <div class="table-container">
        <table class="activity-table">
          <thead>
            <tr>
              <th>{{ t('activity.table.time') }}</th>
              <th>{{ t('activity.table.action') }}</th>
              <th>{{ t('activity.table.entity') }}</th>
              <th>{{ t('activity.table.reference') }}</th>
              <th>{{ t('activity.table.detail') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in entries" :key="entry.id">
              <td class="col-time">{{ formatTimestamp(entry.timestamp) }}</td>
              <td><span :class="['badge', actionClass(entry.action)]">{{ label('actions', entry.action) }}</span></td>
              <td>{{ label('entities', entry.entity) }}</td>
              <td class="col-ref">{{ entry.entity_id }}</td>
              <!-- detail is free text from the server, shown as is -->
              <td class="col-detail">{{ entry.detail }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const ENTRY_LIMIT = 100

export default {
  name: 'ActivityLog',
  setup() {
    const { t, currentLocale } = useI18n()
    const loading = ref(true)
    const error = ref(null)
    const entries = ref([])

    // The audit log has no warehouse or category, so global filters are intentionally ignored
    const loadEntries = async () => {
      try {
        loading.value = true
        error.value = null
        entries.value = await api.getAuditLog(ENTRY_LIMIT)
      } catch (err) {
        error.value = t('activity.loadError')
        console.error('Failed to load activity log:', err)
      } finally {
        loading.value = false
      }
    }

    const formatTimestamp = (value) => {
      const date = new Date(value)
      if (isNaN(date.getTime())) return value
      return date.toLocaleString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    // Unknown values from a newer server fall back to the raw string
    const label = (group, value) => {
      const key = `activity.${group}.${value}`
      const text = t(key)
      return text === key ? value : text
    }

    const actionClass = (action) => ({ created: 'success', updated: 'info', deleted: 'danger' }[action] || 'info')

    onMounted(loadEntries)

    return { t, loading, error, entries, loadEntries, formatTimestamp, label, actionClass }
  }
}
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.refresh-button {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-body);
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.refresh-button:hover:not(:disabled) {
  background: var(--color-surface-muted);
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: 3rem 1.25rem;
}

.col-time {
  white-space: nowrap;
}

.col-ref {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.813rem;
  white-space: nowrap;
}

.col-detail {
  min-width: 14rem;
}
</style>
