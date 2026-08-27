from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_locked = fields.Boolean(
        string='Cost Locked', compute='_compute_cost_locked',
        help="When on (set in Inventory Settings), the product Cost field is "
             "read-only on product forms.")
    cost_sheet_ids = fields.One2many(
        'product.cost.sheet', 'product_tmpl_id', string='Cost Sheets')
    cost_sheet_count = fields.Integer(
        string='Cost Sheet Count', compute='_compute_cost_sheet_count')
    lc_total_added = fields.Monetary(
        string='Landed Cost Added', compute='_compute_lc_added',
        currency_field='cost_currency_id')
    lc_unit_added = fields.Monetary(
        string='Landed Cost / Unit', compute='_compute_lc_added',
        currency_field='cost_currency_id',
        help="Landed cost per unit that has actually been posted to this product "
             "(from validated landed costs). Confirms landed costs were applied.")

    @api.depends('cost_sheet_ids')
    def _compute_cost_sheet_count(self):
        for tmpl in self:
            tmpl.cost_sheet_count = len(tmpl.cost_sheet_ids)

    def _compute_lc_added(self):
        Adj = self.env['stock.valuation.adjustment.lines'].sudo()
        for tmpl in self:
            variant_ids = tmpl.product_variant_ids.ids
            lines = Adj.browse()
            if variant_ids:
                lines = Adj.search([
                    ('product_id', 'in', variant_ids),
                    ('cost_id.state', '=', 'done'),
                ])
            total = sum(lines.mapped('additional_landed_cost'))
            qty = sum(lines.mapped('quantity'))
            tmpl.lc_total_added = total
            tmpl.lc_unit_added = (total / qty) if qty else 0.0

    def _compute_cost_locked(self):
        locked = self.env['ir.config_parameter'].sudo().get_param(
            'landed_cost_breakdown.cost_locked')
        locked = locked in ('True', 'true', '1', 1, True)
        for tmpl in self:
            tmpl.cost_locked = locked

    def action_view_cost_sheets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Breakdown'),
            'res_model': 'product.cost.sheet',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {'default_product_id': self.product_variant_id.id},
        }

    def action_new_cost_sheet(self):
        self.ensure_one()
        sheet = self.env['product.cost.sheet'].create({
            'product_id': self.product_variant_id.id,
        })
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

    def action_show_cost_breakdown(self):
        """Small icon button next to Cost: open a live breakdown preview
        (reuses the latest draft sheet, rebuilt to the current cost) in a
        dialog from which it can be printed / downloaded as PDF."""
        self.ensure_one()
        Sheet = self.env['product.cost.sheet']
        sheet = Sheet.search([
            ('product_tmpl_id', '=', self.id),
            ('state', '=', 'draft'),
        ], order='date desc', limit=1)
        if not sheet:
            sheet = Sheet.create({'product_id': self.product_variant_id.id})
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
