from odoo import _, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_show_cost_breakdown(self):
        """Open the cost breakdown preview for this specific variant."""
        self.ensure_one()
        Sheet = self.env['product.cost.sheet']
        sheet = Sheet.search([
            ('product_id', '=', self.id),
            ('state', '=', 'draft'),
        ], order='date desc', limit=1)
        if not sheet:
            sheet = Sheet.create({'product_id': self.id})
        sheet.action_build_breakdown()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Breakdown'),
            'res_model': 'product.cost.sheet',
            'res_id': sheet.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
