{
    'name': 'Landed Cost Breakdown',
    'version': '19.0.3.1.0',
    'summary': 'See what every product cost is made of — purchase price plus freight, duty, labour and overhead, tagged per landed cost line, per unit, traceable to its source document.',
    'description': """
Landed Cost Breakdown
=====================
Management-accounting oriented product costing on top of Odoo 19 valuation.

Standard valuation gives you one cost per product and no way to see inside it.
Landed costs disappear into inventory value as an anonymous lump.

* Tags every landed cost line with a cost component (Freight, Duty/Tax, Direct
  Labour, Direct Other, Overhead) so its contribution to the product cost stays
  visible.
* Product Cost Sheet: a versioned, printable breakdown of how a product's cost
  is composed (purchase / base + landed components), per unit, reconciled to the
  actual cost, with a source link from every line back to the purchase order or
  landed cost it came from.
* Cost history per receipt — base cost, landed cost and batch cost per unit —
  plus the remaining stock layers behind the current cost.
* Answers "did the landed cost actually get added?" with a live per-unit
  indicator on the product.
* Locks the product Cost field; a gated "Release to Update Cost" button unlocks
  it, and releasing a cost sheet writes the total back to the product cost
  (logged).
* Adds a **Cancel** button to posted landed costs. It cancels the journal entry
  the landed cost posted — no reversing entry, no negative mirror document —
  stamps the record Cancelled, and re-values the receipts it was loaded onto, so
  a wrong cost leaves the breakdown entirely.
* QWeb PDF report of the cost breakdown for accountants.

Works with Standard, FIFO and Average (AVCO) valuation. (LIFO is not supported by
Odoo / IFRS.)
    """,


    'author': 'Aurax (Pvt) Ltd',
    'support': 'support.aurax@gmail.com',
    'website': 'https://aurax.dev',
    'category': 'Accounting/Inventory',
    'depends': [
        'stock_account',
        'stock_landed_costs',
        'purchase',
        'account',
    ],
    'data': [
        'security/cost_security.xml',
        'security/ir.model.access.csv',
        'data/cost_sequence.xml',
        'data/profitability_tiers.xml',
        'report/cost_sheet_report.xml',
        'report/cost_sheet_templates.xml',
        'views/res_config_settings_views.xml',
        'views/stock_landed_cost_views.xml',
        'views/product_cost_sheet_views.xml',
        'views/profitability_tier_views.xml',
        'views/product_views.xml',
        'views/cost_menus.xml',
        'views/costing_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
