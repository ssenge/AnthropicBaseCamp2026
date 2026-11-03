<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div
          ref="dialogRef"
          class="modal-container"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          @click.stop
          @keydown="trapFocus"
        >
          <div class="modal-header">
            <h3 :id="titleId" class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button
              ref="closeRef"
              type="button"
              class="close-button"
              :aria-label="t('purchaseOrder.closeLabel')"
              @click="close"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Backlog item context, shared by both modes -->
            <div class="item-summary">
              <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
              <div class="item-meta">
                <span>{{ backlogItem.item_sku }}</span>
                <span>{{ t('purchaseOrder.shortage') }}: {{ t('purchaseOrder.units', { count: shortage }) }}</span>
              </div>
            </div>

            <!-- View mode -->
            <template v-if="mode === 'view'">
              <div v-if="loadingPO" class="state-message" role="status">{{ t('common.loading') }}</div>
              <div v-else-if="poError" class="error-box" role="alert">{{ poError }}</div>
              <dl v-else-if="purchaseOrder" class="po-details">
                <div class="detail">
                  <dt>{{ t('purchaseOrder.poNumber') }}</dt>
                  <dd class="mono">{{ purchaseOrder.id }}</dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.status') }}</dt>
                  <dd><span class="badge info">{{ statusLabel(purchaseOrder.status) }}</span></dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.supplier') }}</dt>
                  <dd>{{ purchaseOrder.supplier_name }}</dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.quantity') }}</dt>
                  <dd>{{ purchaseOrder.quantity.toLocaleString() }}</dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.unitCost') }}</dt>
                  <dd>{{ formatCurrencyWithDecimals(purchaseOrder.unit_cost, currentCurrency, 2) }}</dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.total') }}</dt>
                  <dd><strong>{{ formatCurrencyWithDecimals(purchaseOrder.quantity * purchaseOrder.unit_cost, currentCurrency, 2) }}</strong></dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.expectedDelivery') }}</dt>
                  <dd>{{ formatDate(purchaseOrder.expected_delivery_date) }}</dd>
                </div>
                <div class="detail">
                  <dt>{{ t('purchaseOrder.createdDate') }}</dt>
                  <dd>{{ formatDate(purchaseOrder.created_date) }}</dd>
                </div>
                <div class="detail wide">
                  <dt>{{ t('purchaseOrder.notesLabel') }}</dt>
                  <dd class="notes">{{ purchaseOrder.notes || t('purchaseOrder.noNotes') }}</dd>
                </div>
              </dl>
            </template>

            <!-- Create mode -->
            <form v-else id="po-form" class="po-form" novalidate @submit.prevent="submit">
              <div class="field">
                <label for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                <select id="po-supplier" v-model="form.supplier" required :disabled="loadingSuppliers">
                  <option value="" disabled>{{ loadingSuppliers ? t('common.loading') : t('purchaseOrder.selectSupplier') }}</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.name">
                    {{ t('purchaseOrder.supplierOption', { name: s.name, days: s.lead_time_days, rating: s.rating }) }}
                  </option>
                </select>
                <p v-if="suppliersError" class="field-error" role="alert">{{ suppliersError }}</p>
              </div>

              <div class="field-row">
                <div class="field">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input id="po-quantity" v-model.number="form.quantity" type="number" min="1" step="1" required inputmode="numeric" />
                </div>
                <div class="field">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input
                    id="po-unit-cost"
                    v-model.number="form.unitCost"
                    type="number"
                    min="0.01"
                    step="0.01"
                    required
                    inputmode="decimal"
                    aria-describedby="po-unit-cost-hint"
                  />
                  <p id="po-unit-cost-hint" class="hint">{{ t('purchaseOrder.unitCostHint') }}</p>
                </div>
              </div>

              <div class="field">
                <label for="po-date">{{ t('purchaseOrder.expectedDelivery') }}</label>
                <input id="po-date" v-model="form.date" type="date" :min="today" required aria-describedby="po-date-hint" />
                <p id="po-date-hint" class="hint">{{ t('purchaseOrder.deliveryHint') }}</p>
              </div>

              <div class="field">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea id="po-notes" v-model="form.notes" rows="3" maxlength="500"></textarea>
              </div>

              <div class="total-row">
                <span>{{ t('purchaseOrder.total') }}</span>
                <strong>{{ formatCurrencyWithDecimals(total, currentCurrency, 2) }}</strong>
              </div>

              <div v-if="submitError" class="error-box" role="alert">{{ submitError }}</div>
            </form>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            <button
              v-if="mode !== 'view'"
              type="submit"
              form="po-form"
              class="btn-primary"
              :disabled="!isValid || submitting"
            >
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

let modalCounter = 0

// Local date as YYYY-MM-DD (toISOString would shift the day for non-UTC users)
const toDateInput = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: { type: Boolean, default: false },
    backlogItem: { type: Object, default: null },
    mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, currentLocale, currentCurrency, translateProductName } = useI18n()
    const titleId = `po-modal-title-${++modalCounter}`

    const dialogRef = ref(null)
    const closeRef = ref(null)
    let previouslyFocused = null

    const suppliers = ref([])
    const loadingSuppliers = ref(false)
    const suppliersError = ref(null)

    const purchaseOrder = ref(null)
    const loadingPO = ref(false)
    const poError = ref(null)

    const submitting = ref(false)
    const submitError = ref(null)

    const form = reactive({ supplier: '', quantity: 1, unitCost: null, date: '', notes: '' })
    const today = computed(() => toDateInput(new Date()))

    const shortage = computed(() => {
      if (!props.backlogItem) return 0
      return Math.max(0, props.backlogItem.quantity_needed - props.backlogItem.quantity_available)
    })

    const selectedSupplier = computed(() => suppliers.value.find((s) => s.name === form.supplier) || null)

    const total = computed(() => {
      const qty = Number(form.quantity)
      const cost = Number(form.unitCost)
      return Number.isFinite(qty) && Number.isFinite(cost) ? qty * cost : 0
    })

    const isValid = computed(() => {
      const qty = Number(form.quantity)
      const cost = Number(form.unitCost)
      return (
        !!form.supplier &&
        Number.isInteger(qty) && qty >= 1 &&
        form.unitCost !== null && form.unitCost !== '' && Number.isFinite(cost) && cost >= 0.01 &&
        /^\d{4}-\d{2}-\d{2}$/.test(form.date)
      )
    })

    // Delivery date follows the supplier's lead time; it can still be edited afterwards
    watch(selectedSupplier, (supplier) => {
      if (!supplier) return
      const d = new Date()
      d.setDate(d.getDate() + supplier.lead_time_days)
      form.date = toDateInput(d)
    })

    const resetForm = () => {
      form.supplier = ''
      // Default to the shortage; unit cost stays empty because no price data exists
      form.quantity = shortage.value || 1
      form.unitCost = null
      form.date = ''
      form.notes = ''
      submitError.value = null
      submitting.value = false
    }

    // Server errors carry `detail`: a string, or a list of validation entries for 422
    const describeError = (err, fallback) => {
      const detail = err && err.response && err.response.data && err.response.data.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        return detail
          .map((d) => {
            const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : ''
            return field ? `${field}: ${d.msg}` : d.msg
          })
          .join('; ')
      }
      return fallback
    }

    const loadSuppliers = async () => {
      loadingSuppliers.value = true
      suppliersError.value = null
      try {
        suppliers.value = await api.getSuppliers()
      } catch (err) {
        console.error('Failed to load suppliers:', err)
        suppliersError.value = describeError(err, t('purchaseOrder.suppliersLoadError'))
      } finally {
        loadingSuppliers.value = false
      }
    }

    const loadPurchaseOrder = async () => {
      loadingPO.value = true
      poError.value = null
      purchaseOrder.value = null
      const requestedId = props.backlogItem.id
      try {
        const po = await api.getPurchaseOrderByBacklogItem(requestedId)
        // Ignore a stale response if the modal moved on to another item
        if (props.backlogItem && props.backlogItem.id === requestedId) purchaseOrder.value = po
      } catch (err) {
        console.error('Failed to load purchase order:', err)
        poError.value = describeError(err, t('purchaseOrder.loadError'))
      } finally {
        loadingPO.value = false
      }
    }

    const submit = async () => {
      if (!isValid.value || submitting.value) return
      submitting.value = true
      submitError.value = null
      try {
        const payload = {
          backlog_item_id: props.backlogItem.id,
          supplier_name: form.supplier,
          quantity: Number(form.quantity),
          unit_cost: Number(form.unitCost),
          expected_delivery_date: form.date
        }
        const notes = form.notes.trim()
        if (notes) payload.notes = notes
        const po = await api.createPurchaseOrder(payload)
        emit('po-created', po)
      } catch (err) {
        console.error('Failed to create purchase order:', err)
        submitError.value = describeError(err, t('purchaseOrder.createError'))
      } finally {
        submitting.value = false
      }
    }

    const close = () => emit('close')

    const onKeydown = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        close()
      }
    }

    // Keep Tab inside the dialog while it is open
    const trapFocus = (event) => {
      if (event.key !== 'Tab' || !dialogRef.value) return
      const focusable = dialogRef.value.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    watch(
      () => [props.isOpen, props.backlogItem && props.backlogItem.id, props.mode],
      async (now, before) => {
        const open = now[0]
        const wasOpen = !!(before && before[0])
        if (!open || !props.backlogItem) return
        if (!wasOpen) {
          previouslyFocused = document.activeElement
          document.addEventListener('keydown', onKeydown)
        }
        if (props.mode === 'view') {
          loadPurchaseOrder()
        } else {
          resetForm()
          if (suppliers.value.length === 0) loadSuppliers()
        }
        await nextTick()
        if (closeRef.value) closeRef.value.focus()
      },
      { immediate: true }
    )

    watch(
      () => props.isOpen,
      (open) => {
        if (open) return
        document.removeEventListener('keydown', onKeydown)
        if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus()
        previouslyFocused = null
      }
    )

    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    const formatDate = (dateString) => {
      if (!dateString) return '-'
      // Date-only strings parse as UTC; add a time so the local day is kept
      const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(dateString) ? `${dateString}T00:00:00` : dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    // Unknown statuses fall back to the raw server value
    const statusLabel = (status) => {
      const key = `purchaseOrder.statusValues.${String(status).toLowerCase()}`
      const label = t(key)
      return label === key ? status : label
    }

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrencyWithDecimals,
      titleId,
      dialogRef,
      closeRef,
      suppliers,
      loadingSuppliers,
      suppliersError,
      purchaseOrder,
      loadingPO,
      poError,
      submitting,
      submitError,
      form,
      today,
      shortage,
      total,
      isValid,
      submit,
      close,
      trapFocus,
      formatDate,
      statusLabel
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.close-button:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.5rem;
}

.item-summary {
  padding: 0.875rem 1rem;
  background: var(--color-surface-muted);
  border-radius: var(--radius-control);
  margin-bottom: 1.25rem;
}

.item-name {
  font-weight: 700;
  color: var(--color-text);
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  margin-top: 0.25rem;
  font-size: 0.813rem;
  color: var(--color-text-muted);
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-width: 0;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  font-size: 0.813rem;
  font-weight: 600;
  color: var(--color-text-body);
}

input,
select,
textarea {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-control);
  font-family: inherit;
  font-size: 0.875rem;
  color: var(--color-text);
  background: var(--color-surface);
}

textarea {
  resize: vertical;
}

input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.field-error {
  font-size: 0.813rem;
  color: var(--color-danger);
}

.total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--color-accent-soft);
  border-radius: var(--radius-control);
  color: var(--color-text);
}

.total-row strong {
  font-size: 1.125rem;
}

.error-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-control);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}

.state-message {
  text-align: center;
  padding: 2rem 0;
  color: var(--color-text-muted);
}

.po-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.5rem;
}

.detail {
  min-width: 0;
}

.detail.wide {
  grid-column: 1 / -1;
}

dt {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

dd {
  color: var(--color-text);
  font-size: 0.938rem;
  overflow-wrap: anywhere;
}

.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: var(--color-accent);
}

.notes {
  white-space: pre-wrap;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: var(--radius-control);
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  font-family: inherit;
  transition: background-color 0.15s ease;
}

.btn-secondary {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-body);
}

.btn-secondary:hover {
  background: var(--color-border);
}

.btn-primary {
  background: var(--color-accent);
  border: 1px solid var(--color-accent);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .field-row,
  .po-details {
    grid-template-columns: 1fr;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .modal-enter-active,
  .modal-leave-active {
    transition: none;
  }
}
</style>
