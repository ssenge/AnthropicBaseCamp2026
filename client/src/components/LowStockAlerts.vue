<template>
  <div ref="rootRef" class="low-stock">
    <button
      type="button"
      class="bell-button"
      :aria-expanded="String(open)"
      aria-haspopup="true"
      aria-controls="low-stock-panel"
      :aria-label="t('lowStock.bellLabel', { count: alerts.length })"
      @click="open = !open"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.7 21a2 2 0 01-3.4 0" />
      </svg>
      <span v-if="alerts.length > 0" class="badge-count" aria-hidden="true">{{ alerts.length }}</span>
    </button>

    <div v-if="open" id="low-stock-panel" class="panel" role="region" :aria-label="t('lowStock.title')">
      <div class="panel-title">{{ t('lowStock.title') }}</div>
      <p v-if="alerts.length === 0" class="empty">{{ t('lowStock.empty') }}</p>
      <ul v-else class="alert-list">
        <li v-for="alert in visibleAlerts" :key="alert.id" class="alert-item">
          <div class="alert-top">
            <span class="alert-name">{{ translateProductName(alert.name) }}</span>
            <span :class="['severity', alert.severity]">{{ t(`lowStock.severity.${alert.severity}`) }}</span>
          </div>
          <div class="alert-meta">{{ alert.sku }} &middot; {{ translateWarehouse(alert.warehouse) }}</div>
          <div class="alert-meta">{{ t('lowStock.onHand', { onHand: alert.quantity_on_hand, reorder: alert.reorder_point }) }}</div>
        </li>
      </ul>
      <p v-if="hiddenCount > 0" class="more">{{ t('lowStock.moreItems', { count: hiddenCount }) }}</p>
      <router-link to="/inventory" class="panel-link" @click="open = false">{{ t('lowStock.viewInventory') }}</router-link>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

const MAX_VISIBLE = 8

export default {
  name: 'LowStockAlerts',
  setup() {
    const { t, translateProductName, translateWarehouse } = useI18n()
    // Inventory has no time dimension, so only location and category apply
    const { selectedLocation, selectedCategory } = useFilters()

    const rootRef = ref(null)
    const open = ref(false)
    const alerts = ref([])
    let requestSeq = 0

    const visibleAlerts = computed(() => alerts.value.slice(0, MAX_VISIBLE))
    const hiddenCount = computed(() => Math.max(0, alerts.value.length - MAX_VISIBLE))

    const loadAlerts = async () => {
      const seq = ++requestSeq
      try {
        const result = await api.getLowStock({
          warehouse: selectedLocation.value,
          category: selectedCategory.value
        })
        if (seq === requestSeq) alerts.value = result
      } catch (err) {
        // A failed fetch must not break the shell: hide the badge and carry on
        console.error('Failed to load low stock alerts:', err)
        if (seq === requestSeq) alerts.value = []
      }
    }

    const onDocumentClick = (event) => {
      if (open.value && rootRef.value && !rootRef.value.contains(event.target)) open.value = false
    }

    const onKeydown = (event) => {
      if (event.key === 'Escape' && open.value) {
        open.value = false
        const button = rootRef.value && rootRef.value.querySelector('.bell-button')
        if (button) button.focus()
      }
    }

    watch([selectedLocation, selectedCategory], loadAlerts)

    onMounted(() => {
      loadAlerts()
      document.addEventListener('click', onDocumentClick)
      document.addEventListener('keydown', onKeydown)
    })

    onBeforeUnmount(() => {
      document.removeEventListener('click', onDocumentClick)
      document.removeEventListener('keydown', onKeydown)
    })

    return { t, translateProductName, translateWarehouse, rootRef, open, alerts, visibleAlerts, hiddenCount }
  }
}
</script>

<style scoped>
.low-stock {
  position: relative;
}

.bell-button {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  color: var(--color-text-body);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.bell-button:hover {
  background: var(--color-surface-muted);
}

.badge-count {
  position: absolute;
  top: -0.375rem;
  right: -0.375rem;
  min-width: 1.125rem;
  height: 1.125rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: var(--color-danger);
  color: #ffffff;
  font-size: 0.688rem;
  font-weight: 700;
  line-height: 1.125rem;
  text-align: center;
}

.panel {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  z-index: 300;
  width: 22rem;
  max-width: calc(100vw - 2rem);
  max-height: 70vh;
  overflow-y: auto;
  padding: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15);
}

.panel-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text);
  padding: 0.25rem 0.25rem 0.5rem;
}

.empty,
.more {
  padding: 0.5rem 0.25rem;
  font-size: 0.813rem;
  color: var(--color-text-muted);
}

.alert-list {
  list-style: none;
}

.alert-item {
  padding: 0.5rem 0.25rem;
  border-top: 1px solid var(--color-border);
}

.alert-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.alert-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text);
  min-width: 0;
  overflow-wrap: anywhere;
}

.alert-meta {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.125rem;
}

.severity {
  flex-shrink: 0;
  padding: 0.125rem 0.5rem;
  border-radius: 6px;
  font-size: 0.688rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.severity.critical {
  background: #fecaca;
  color: #991b1b;
}

.severity.warning {
  background: #fed7aa;
  color: #92400e;
}

.panel-link {
  display: block;
  margin-top: 0.5rem;
  padding: 0.5rem;
  border-top: 1px solid var(--color-border);
  text-align: center;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.panel-link:hover {
  text-decoration: underline;
}

/* On phones the bell sits mid-row, so anchor the panel to the viewport instead of the bell */
@media (max-width: 480px) {
  .low-stock {
    position: static;
  }

  .panel {
    position: fixed;
    top: auto;
    /* Clear the fixed icon sidebar */
    left: calc(var(--sidebar-w) + 0.5rem);
    right: 0.5rem;
    width: auto;
    max-width: none;
    margin-top: 0.5rem;
  }
}
</style>
