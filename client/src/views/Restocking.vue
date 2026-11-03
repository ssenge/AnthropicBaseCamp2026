<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="initialLoading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <label class="budget-label" for="budget-slider">{{ t('restocking.budgetSlider') }}</label>
        <div class="budget-row">
          <input
            id="budget-slider"
            v-model.number="budget"
            class="budget-slider"
            type="range"
            min="0"
            :max="sliderMax"
            :step="BUDGET_STEP"
            :disabled="sliderMax === 0"
          />
          <span class="budget-amount">{{ formatCurrency(budget, currentCurrency) }}</span>
        </div>
        <div class="budget-hint">
          {{ t('restocking.maxBudget', { amount: formatCurrency(maxBudget, currentCurrency) }) }}
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatCurrency(budget, currentCurrency) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.recommendedSpend') }}</div>
          <div class="stat-value">{{ formatCurrency(plan.total_cost, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatCurrency(Math.max(budget - plan.total_cost, 0), currentCurrency) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ plan.recommendations.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="!canPlaceOrder"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="orderSuccess" class="notice success-notice" role="status">
          {{ t('restocking.orderPlaced', {
            orderNumber: orderSuccess.order_number,
            date: formatDate(orderSuccess.expected_delivery)
          }) }}
          <router-link to="/orders" class="notice-link">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="orderError" class="notice error-notice" role="alert">{{ orderError }}</div>
        <div v-if="loadError" class="notice error-notice" role="alert">{{ loadError }}</div>

        <div v-if="plan.recommendations.length === 0" class="empty-state">
          {{ maxBudget === 0 ? t('restocking.noNeeds') : t('restocking.empty') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.onHand') }}</th>
                <th class="num">{{ t('restocking.table.needed') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineCost') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in plan.recommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>{{ translateProductName(rec.item_name) }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t(`trends.${rec.trend}`) }}</span>
                </td>
                <td class="num">{{ rec.on_hand.toLocaleString() }}</td>
                <td class="num">{{ rec.needed.toLocaleString() }}</td>
                <td class="num">
                  <strong>{{ rec.quantity.toLocaleString() }}</strong>
                  <span
                    v-if="rec.quantity < rec.needed"
                    class="badge warning partial-badge"
                    :title="t('restocking.partialHint')"
                  >{{ t('restocking.partial') }}</span>
                </td>
                <td class="num">{{ formatMoney(rec.unit_cost) }}</td>
                <td class="num"><strong>{{ formatMoney(rec.line_cost) }}</strong></td>
                <td class="num">{{ t('restocking.days', { count: rec.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 100
const DEBOUNCE_MS = 250

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const initialLoading = ref(true)
    const error = ref(null)
    const loadError = ref(null)
    const budget = ref(0)
    const maxBudget = ref(0)
    const plan = ref({ total_cost: 0, recommendations: [] })
    const planPending = ref(false)

    const submitting = ref(false)
    const orderSuccess = ref(null)
    const orderError = ref(null)

    // The slider must be able to reach a value that covers every need, so round max up to the step
    const sliderMax = computed(() => Math.ceil(maxBudget.value / BUDGET_STEP) * BUDGET_STEP)

    // Placing is also blocked while the shown plan is stale (debounce running or request in flight)
    const canPlaceOrder = computed(() =>
      plan.value.recommendations.length > 0 && !submitting.value && !planPending.value
    )

    // Each request gets an id; only the latest one may write state, so a slow
    // earlier response can't overwrite the result for a newer slider position
    let requestSeq = 0
    let debounceTimer = null

    const loadPlan = async (amount) => {
      const seq = ++requestSeq
      planPending.value = true
      try {
        const result = await api.getRestockRecommendations(amount)
        if (seq !== requestSeq) return
        plan.value = result
        maxBudget.value = result.max_budget
        loadError.value = null
        // Needs can shrink after an order; keep the slider inside its range
        if (budget.value > sliderMax.value) budget.value = sliderMax.value
      } catch (err) {
        if (seq !== requestSeq) return
        loadError.value = t('restocking.loadError', { message: err.message })
      } finally {
        if (seq === requestSeq) planPending.value = false
      }
    }

    watch(budget, (value) => {
      // Mark stale immediately so the order button can't submit an outdated plan
      planPending.value = true
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => loadPlan(value), DEBOUNCE_MS)
    })

    const init = async () => {
      try {
        // budget=0 is the cheap way to learn max_budget
        const base = await api.getRestockRecommendations(0)
        maxBudget.value = base.max_budget
        // Default to about a quarter of full coverage, rounded to the slider step
        const start = Math.round(base.max_budget / 4 / BUDGET_STEP) * BUDGET_STEP
        // Setting budget triggers the debounced watcher; skip it and load directly
        budget.value = Math.min(start, sliderMax.value)
        clearTimeout(debounceTimer)
        await loadPlan(budget.value)
      } catch (err) {
        error.value = t('restocking.loadError', { message: err.message })
      } finally {
        initialLoading.value = false
      }
    }

    // The backend returns 400/422 with `detail`; 422 detail is a list of validation errors
    const extractError = (err) => {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return detail.map(d => d.msg).join('; ')
      return t('restocking.orderFailed')
    }

    const placeOrder = async () => {
      if (!canPlaceOrder.value) return
      submitting.value = true
      orderSuccess.value = null
      orderError.value = null
      try {
        // Order exactly what is displayed, using the budget that produced it
        const order = await api.createRestockOrder(plan.value.budget, plan.value.recommendations)
        orderSuccess.value = order
        clearTimeout(debounceTimer)
        await loadPlan(budget.value)
      } catch (err) {
        orderError.value = extractError(err)
      } finally {
        submitting.value = false
      }
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    // Unit costs are fractional (e.g. 2.40), so show cents in USD; JPY rounds to whole yen
    const formatMoney = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

    onMounted(init)
    onBeforeUnmount(() => {
      clearTimeout(debounceTimer)
      // Invalidate any in-flight request
      requestSeq++
    })

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrency,
      formatMoney,
      formatDate,
      BUDGET_STEP,
      initialLoading,
      error,
      loadError,
      budget,
      maxBudget,
      sliderMax,
      plan,
      submitting,
      canPlaceOrder,
      orderSuccess,
      orderError,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.75rem;
}

/* The amount drops below the slider when both can't fit, rather than overflowing the card */
.budget-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1.25rem;
}

.card-header {
  flex-wrap: wrap;
  gap: 0.75rem;
}

.budget-slider {
  flex: 1 1 12rem;
  min-width: 0;
  accent-color: #2563eb;
  cursor: pointer;
}

.budget-slider:disabled {
  cursor: not-allowed;
}

.budget-amount {
  min-width: 8rem;
  margin-left: auto;
  text-align: right;
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-hint {
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.place-order-btn {
  padding: 0.5rem 1.25rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.notice {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.success-notice {
  background: #d1fae5;
  color: #065f46;
}

.error-notice {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.notice-link {
  margin-left: 0.5rem;
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
}

.empty-state {
  padding: 3rem;
  text-align: center;
  color: #64748b;
}

.num {
  text-align: right;
}

.partial-badge {
  margin-left: 0.5rem;
}
</style>
