<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div v-if="quarterlyData.length === 0" class="empty-state">{{ t('reports.empty') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th>{{ t('reports.quarterly.totalOrders') }}</th>
                <th>{{ t('reports.quarterly.totalRevenue') }}</th>
                <th>{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatCurrency(q.total_revenue, currentCurrency) }}</td>
                <td>{{ formatCurrency(q.avg_order_value, currentCurrency) }}</td>
                <td>
                  <span :class="['badge', getFulfillmentClass(q.fulfillment_rate)]">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthlyTrend.title') }}</h3>
        </div>
        <div v-if="monthlyRows.length === 0" class="empty-state">{{ t('reports.empty') }}</div>
        <div v-else class="chart-container">
          <div class="bar-chart">
            <div v-for="row in monthlyRows" :key="row.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: row.barHeight + 'px' }"
                  :title="row.revenueText"
                ></div>
              </div>
              <div class="bar-label">{{ row.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthOverMonth.title') }}</h3>
        </div>
        <div v-if="monthlyRows.length === 0" class="empty-state">{{ t('reports.empty') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.monthOverMonth.month') }}</th>
                <th>{{ t('reports.monthOverMonth.orders') }}</th>
                <th>{{ t('reports.monthOverMonth.revenue') }}</th>
                <th>{{ t('reports.monthOverMonth.change') }}</th>
                <th>{{ t('reports.monthOverMonth.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthlyRows" :key="row.month">
                <td><strong>{{ row.label }}</strong></td>
                <td>{{ row.order_count }}</td>
                <td>{{ row.revenueText }}</td>
                <td>
                  <span v-if="row.changeText" :class="row.changeClass">{{ row.changeText }}</span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="row.growthText" :class="row.changeClass">{{ row.growthText }}</span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(totalRevenue, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(avgMonthlyRevenue, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const MAX_BAR_HEIGHT = 200

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    // Only the latest request may write state, so a slow response to old filters can't win
    let requestSeq = 0

    const loadData = async () => {
      const seq = ++requestSeq
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        if (seq !== requestSeq) return
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        if (seq !== requestSeq) return
        error.value = t('reports.loadError', { message: err.message })
        console.error('Failed to load reports:', err)
      } finally {
        if (seq === requestSeq) loading.value = false
      }
    }

    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], loadData)

    // Converts "YYYY-MM" to a locale-aware label; falls back to the raw string if malformed
    const formatMonth = (monthStr) => {
      const [year, month] = String(monthStr).split('-').map(Number)
      if (!year || !month) return monthStr
      const date = new Date(year, month - 1, 1)
      if (isNaN(date.getTime())) return monthStr
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short'
      })
    }

    const maxRevenue = computed(() =>
      monthlyData.value.reduce((max, m) => Math.max(max, m.revenue), 0)
    )

    // One row per month that has data. "Previous" is the previous row, which with
    // month/status filters may not be the previous calendar month; no rows are invented.
    const monthlyRows = computed(() => {
      return monthlyData.value.map((m, i) => {
        const prev = i > 0 ? monthlyData.value[i - 1] : null
        const row = {
          ...m,
          label: formatMonth(m.month),
          revenueText: formatCurrency(m.revenue, currentCurrency.value),
          barHeight: maxRevenue.value === 0 ? 0 : (m.revenue / maxRevenue.value) * MAX_BAR_HEIGHT,
          changeText: '',
          growthText: '',
          changeClass: ''
        }
        if (prev) {
          const change = m.revenue - prev.revenue
          const sign = change > 0 ? '+' : change < 0 ? '-' : ''
          row.changeText = sign + formatCurrency(Math.abs(change), currentCurrency.value)
          row.changeClass = change > 0 ? 'positive-change' : change < 0 ? 'negative-change' : ''
          if (prev.revenue === 0) {
            row.growthText = t('reports.notAvailable')
          } else {
            const rate = (change / prev.revenue) * 100
            row.growthText = (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
          }
        }
        return row
      })
    })

    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.revenue, 0)
    )

    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length > 0 ? totalRevenue.value / monthlyData.value.length : 0
    )

    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.order_count, 0)
    )

    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (!best || q.total_revenue > best.total_revenue) best = q
      }
      return best ? best.quarter : '-'
    })

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'success'
      if (rate >= 75) return 'warning'
      return 'danger'
    }

    onMounted(loadData)

    return {
      t,
      currentCurrency,
      formatCurrency,
      loading,
      error,
      quarterlyData,
      monthlyRows,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      getFulfillmentClass
    }
  }
}
</script>

<style scoped>
.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}
</style>
