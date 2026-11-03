from datetime import date, datetime, timedelta
from itertools import count
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, suppliers

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None

class RestockRecommendation(BaseModel):
    item_sku: str
    item_name: str
    trend: str
    on_hand: int
    needed: int
    quantity: int
    unit_cost: float
    line_cost: float
    lead_time_days: int

class RestockPlan(BaseModel):
    budget: float
    max_budget: float
    total_cost: float
    remaining_budget: float
    recommendations: List[RestockRecommendation]

class RestockOrderLine(BaseModel):
    item_sku: str
    quantity: int = Field(gt=0)

class CreateRestockOrderRequest(BaseModel):
    budget: float = Field(ge=0)
    items: List[RestockOrderLine] = Field(min_length=1)

class RestockOrder(BaseModel):
    id: str
    order_number: str
    status: str
    submitted_at: str
    expected_delivery: str
    lead_time_days: int
    total_cost: float
    items: List[RestockRecommendation]

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int = Field(gt=0)
    unit_cost: float = Field(gt=0)
    expected_delivery_date: date
    notes: Optional[str] = None

class Supplier(BaseModel):
    id: str
    name: str
    lead_time_days: int
    rating: float
    contact_email: str

class LowStockAlert(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    shortfall: int
    severity: Literal['critical', 'warning']

class AuditEntry(BaseModel):
    id: int
    timestamp: str
    action: str
    entity: str
    entity_id: str
    detail: str

# In-memory like the other mock data: the trail starts empty on every restart
audit_log = []
audit_ids = count(1)

def record_audit(action: str, entity: str, entity_id: str, detail: str) -> None:
    """Append to the audit trail. Call only after a write has succeeded."""
    audit_log.append({
        'id': next(audit_ids),
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'action': action,
        'entity': entity,
        'entity_id': entity_id,
        'detail': detail
    })

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

# Declared before /api/inventory/{item_id}, which would otherwise capture "low-stock" as an id
@app.get("/api/inventory/low-stock", response_model=List[LowStockAlert])
def get_low_stock_alerts(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get items at or below their reorder point, most depleted first"""
    alerts = []
    for item in apply_filters(inventory_items, warehouse, category):
        if item["quantity_on_hand"] <= item["reorder_point"]:
            alerts.append({
                **item,
                'shortfall': item["reorder_point"] - item["quantity_on_hand"],
                # Below half the reorder point leaves little buffer for a normal delivery lead time
                'severity': 'critical' if item["quantity_on_hand"] < item["reorder_point"] / 2 else 'warning'
            })
    alerts.sort(key=lambda a: (a['quantity_on_hand'] / a['reorder_point'] if a['reorder_point'] else 0, a['sku']))
    return alerts

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

# In-memory like the other mock data: submitted orders are lost on restart
restock_orders = []
TREND_PRIORITY = {'increasing': 0, 'stable': 1, 'decreasing': 2}

def restock_needs() -> list:
    """Units each forecast SKU is short of its forecast, most urgent first"""
    on_hand = {}
    for item in inventory_items:
        on_hand[item['sku']] = on_hand.get(item['sku'], 0) + item['quantity_on_hand']

    needs = []
    for forecast in demand_forecasts:
        # A SKU missing from inventory is treated as out of stock, so it needs its full forecast
        stock = on_hand.get(forecast['item_sku'], 0)
        needed = forecast['forecasted_demand'] - stock
        if needed > 0:
            needs.append({
                'item_sku': forecast['item_sku'],
                'item_name': forecast['item_name'],
                'trend': forecast['trend'],
                'on_hand': stock,
                'needed': needed,
                'unit_cost': forecast['unit_cost'],
                'lead_time_days': forecast['lead_time_days'],
                'growth': (forecast['forecasted_demand'] - forecast['current_demand']) / forecast['current_demand']
            })
    needs.sort(key=lambda n: (TREND_PRIORITY.get(n['trend'], 3), -n['growth'], n['item_sku']))
    return needs

def restock_line(need: dict, quantity: int) -> dict:
    return {
        'item_sku': need['item_sku'],
        'item_name': need['item_name'],
        'trend': need['trend'],
        'on_hand': need['on_hand'],
        'needed': need['needed'],
        'quantity': quantity,
        'unit_cost': need['unit_cost'],
        'line_cost': round(quantity * need['unit_cost'], 2),
        'lead_time_days': need['lead_time_days']
    }

@app.get("/api/restocking/recommendations", response_model=RestockPlan)
def get_restock_recommendations(budget: float = Query(ge=0)):
    """Recommend what to restock for a budget, filling the most urgent SKUs first"""
    needs = restock_needs()
    remaining = budget
    recommendations = []
    for need in needs:
        # Partial lines are allowed so the budget is spent on urgent SKUs before cheaper, less urgent ones
        quantity = min(need['needed'], int(remaining // need['unit_cost']))
        if quantity > 0:
            line = restock_line(need, quantity)
            recommendations.append(line)
            remaining = round(remaining - line['line_cost'], 2)

    return {
        'budget': budget,
        'max_budget': round(sum(n['needed'] * n['unit_cost'] for n in needs), 2),
        'total_cost': round(sum(r['line_cost'] for r in recommendations), 2),
        'remaining_budget': remaining,
        'recommendations': recommendations
    }

@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restock_order(request: CreateRestockOrderRequest):
    """Submit a restocking order. Prices come from the server, never from the client."""
    needs = {n['item_sku']: n for n in restock_needs()}
    if len({line.item_sku for line in request.items}) != len(request.items):
        raise HTTPException(status_code=400, detail="Duplicate SKU in order")

    lines = []
    for line in request.items:
        need = needs.get(line.item_sku)
        if not need:
            raise HTTPException(status_code=400, detail=f"{line.item_sku} does not need restocking")
        if line.quantity > need['needed']:
            raise HTTPException(status_code=400, detail=f"{line.item_sku}: quantity exceeds the {need['needed']} units needed")
        lines.append(restock_line(need, line.quantity))

    total_cost = round(sum(l['line_cost'] for l in lines), 2)
    if total_cost > request.budget:
        raise HTTPException(status_code=400, detail=f"Order total {total_cost} exceeds budget {request.budget}")

    # The order arrives when its slowest line does
    lead_time_days = max(l['lead_time_days'] for l in lines)
    now = datetime.now()
    order_id = str(len(restock_orders) + 1)
    order = {
        'id': order_id,
        'order_number': f"RST-{now.year}-{int(order_id):04d}",
        'status': 'Submitted',
        'submitted_at': now.isoformat(timespec='seconds'),
        'expected_delivery': (now + timedelta(days=lead_time_days)).isoformat(timespec='seconds'),
        'lead_time_days': lead_time_days,
        'total_cost': total_cost,
        'items': lines
    }
    restock_orders.append(order)
    record_audit('created', 'restock_order', order['order_number'], f"{len(lines)} items, total {total_cost:.2f}")
    return order

@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restock_orders():
    """Get submitted restocking orders, newest first"""
    return list(reversed(restock_orders))

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports with optional filtering"""
    filtered_orders = filter_by_month(apply_filters(orders, warehouse, category, status), month)

    # Calculate quarterly statistics from orders
    quarters = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends with optional filtering"""
    filtered_orders = filter_by_month(apply_filters(orders, warehouse, category, status), month)
    months = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1)
    priority: Literal['high', 'medium', 'low']
    dueDate: date

class Task(CreateTaskRequest):
    id: str
    status: Literal['pending', 'completed']

# In-memory like the other mock data. String ids can't collide with useAuth's numeric mock task ids,
# and the counter never reuses an id after a delete.
tasks = []
task_ids = count(1)

def find_task(task_id: str) -> dict:
    task = next((task for task in tasks if task['id'] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get tasks, newest first"""
    return tasks

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(request: CreateTaskRequest):
    """Create a pending task"""
    task = {**request.model_dump(), 'id': f"task-{next(task_ids)}", 'status': 'pending'}
    tasks.insert(0, task)
    record_audit('created', 'task', task['id'], task['title'])
    return task

@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: str):
    """Flip a task between pending and completed"""
    task = find_task(task_id)
    task['status'] = 'completed' if task['status'] == 'pending' else 'pending'
    record_audit('updated', 'task', task['id'], f"{task['title']}: {task['status']}")
    return task

@app.delete("/api/tasks/{task_id}", response_model=Task)
def delete_task(task_id: str):
    """Delete a task and return it"""
    task = find_task(task_id)
    tasks.remove(task)
    record_audit('deleted', 'task', task['id'], task['title'])
    return task

@app.get("/api/suppliers", response_model=List[Supplier])
def get_suppliers():
    """Get suppliers that purchase orders can be placed with"""
    return suppliers

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create the purchase order that resolves a backlog item"""
    if not any(item["id"] == request.backlog_item_id for item in backlog_items):
        raise HTTPException(status_code=404, detail=f"Backlog item {request.backlog_item_id} not found")
    if any(po["backlog_item_id"] == request.backlog_item_id for po in purchase_orders):
        raise HTTPException(status_code=409, detail=f"Backlog item {request.backlog_item_id} already has a purchase order")
    if not any(supplier["name"] == request.supplier_name for supplier in suppliers):
        raise HTTPException(status_code=400, detail=f"Unknown supplier: {request.supplier_name}")

    po = {
        **request.model_dump(),
        'id': f"PO-{len(purchase_orders) + 1:04d}",
        'expected_delivery_date': request.expected_delivery_date.isoformat(),
        'status': 'Submitted',
        'created_date': datetime.now().isoformat(timespec='seconds')
    }
    purchase_orders.append(po)
    record_audit('created', 'purchase_order', po['id'], f"{po['quantity']} units from {po['supplier_name']}")
    return po

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order(backlog_item_id: str):
    """Get the purchase order for a backlog item"""
    po = next((po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id), None)
    if not po:
        raise HTTPException(status_code=404, detail=f"No purchase order for backlog item {backlog_item_id}")
    return po

@app.get("/api/audit-log", response_model=List[AuditEntry])
def get_audit_log(limit: int = Query(100, ge=1, le=500)):
    """Get recorded write actions, newest first"""
    return audit_log[-limit:][::-1]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
