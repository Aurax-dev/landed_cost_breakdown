from odoo import _, fields, models
from odoo.exceptions import UserError

# Landed cost lines carry a component tag (excludes the base 'purchase' cost).
LANDED_COMPONENT_SELECTION = [
    ('freight', 'Freight / Landed'),
    ('duty', 'Duty / Tax'),
    ('labour', 'Direct Labour'),
    ('other', 'Direct Other'),
    ('overhead', 'Overhead'),
]


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def action_cancel_landed_cost(self):
        """Cancel a posted landed cost in place, without a reversing document.

        Odoo 19 values a stock move from the adjustment lines of landed costs in
        state 'done' (see stock_landed_costs/models/stock_move.py), so flipping
        this cost to 'cancel' and re-valuing the affected moves removes its
        contribution from the stock valuation and the product cost. The journal
        entry it posted is reset to draft and cancelled rather than reversed."""
        for cost in self:
            if cost.state != 'done':
                raise UserError(_("Only a posted landed cost can be cancelled."))
            move = cost.account_move_id
            if move:
                reconciled = move.line_ids.filtered(
                    lambda l: l.matched_debit_ids or l.matched_credit_ids)
                if reconciled:
                    raise UserError(_(
                        "The journal entry %s has reconciled lines. Unreconcile "
                        "them before cancelling this landed cost.", move.name))
                if move.state == 'posted':
                    move.button_draft()
                if move.state != 'cancel':
                    move.button_cancel()
            cost.write({'state': 'cancel'})
            # Re-value the receipts this cost was loaded onto, now that it no
            # longer counts, and let Odoo recompute the product cost.
            cost.valuation_adjustment_lines.move_id._set_value()
            cost.message_post(body=_(
                "Landed cost cancelled. Journal entry %s cancelled and the stock "
                "valuation reverted.", move.name) if move else _(
                "Landed cost cancelled and the stock valuation reverted."))
        return True


class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'

    cost_component = fields.Selection(
        LANDED_COMPONENT_SELECTION, string='Cost Component', default='freight',
        help="Categorizes this landed cost so it appears correctly in the "
             "product cost breakdown (Freight, Duty/Tax, Direct Labour, etc.).")
