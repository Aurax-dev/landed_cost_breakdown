Landed Cost Breakdown
=====================

Cancel a posted landed cost without a reversing entry, tag landed costs by
component, and see exactly how each product's cost was built.

Installation
------------

1. Install the module from the Odoo Apps store or copy it into your
   ``extra-addons`` directory.
2. Update the module list: **Apps → Update Apps List**.
3. Search for *Landed Cost Breakdown* and click **Install**.

Requires ``stock_account``, ``stock_landed_costs``, ``purchase`` and
``account``. Works on Community and Enterprise.

Configuration
-------------

**Access rights.** The module adds a *Cost Manager* group. Only a Cost
Manager can release a cost sheet back onto a product. Grant it under
**Settings → Users & Companies → Users**.

**Cost lock.** In **Inventory → Configuration → Settings**, switch on
*Lock Product Cost* to make the product Cost field read-only everywhere.
With the lock on, the only way a cost changes by hand is through a released
cost sheet.

**Profitability tiers.** Margin bands live under
**Accounting → Configuration → Profitability Tiers**. Each tier has a label,
a minimum margin and a colour.

Cancelling a Landed Cost
------------------------

Standard Odoo refuses to cancel a validated landed cost and tells you to post
a negative one instead. This module adds a **Cancel** button to posted landed
costs (Inventory Managers only), which instead:

1. Resets the journal entry the landed cost posted and cancels it — no
   reversing entry is created.
2. Sets the landed cost to *Cancelled* and stamps a red ribbon on the form.
3. Re-values the receipts the cost was loaded onto, so the stock valuation
   and the product cost drop back to what they were.

Odoo 19 only counts valuation adjustment lines belonging to landed costs in
state *Posted*, so a cancelled cost also disappears from the cost sheet, the
cost history and the *Landed Cost / Unit* indicator.

The button refuses to run when the journal entry has reconciled lines —
unreconcile them first. Odoo's own lock-date and hash checks still apply.

Cost Components
---------------

Every landed cost line gets a **Cost Component**:

- Freight / Landed
- Duty / Tax
- Direct Labour
- Direct Other
- Overhead

The tag carries through to the product cost breakdown, so a landed cost is no
longer a single anonymous number added to inventory value.

Product Cost Sheet
------------------

Open a product and use **Cost Breakdown** to build a sheet. It has three
tabs:

- **Cost Sheet** — purchase cost plus each landed component, per unit, with
  a source link back to the purchase order or landed cost, and the variance
  against the product's current cost.
- **Cost History** — one row per past receipt: date, document, quantity,
  base cost, landed cost and resulting batch cost per unit. Choose a period
  (this month, last quarter, this year, custom) and press *Apply*.
- **Current Cost** — the units still in stock, layer by layer, with each
  layer's unit cost and value.

Press **Print PDF** for a QWeb report of the breakdown.

Releasing a Cost
----------------

A cost sheet starts in *Draft*. A Cost Manager pressing **Release to Update
Cost** writes the sheet total onto the product's cost and records who
released it and when. **Reset to Draft** puts it back for another pass.

Supported Costing Methods
-------------------------

Standard, FIFO and Average (AVCO). LIFO is not supported by Odoo.

Support
-------

Email support.aurax@gmail.com — we aim to answer within 24 hours on business
days.
