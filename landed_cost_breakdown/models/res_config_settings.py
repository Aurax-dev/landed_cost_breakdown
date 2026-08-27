from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_cost_locked = fields.Boolean(
        string='Lock Product Cost',
        config_parameter='landed_cost_breakdown.cost_locked',
        help="Make the product Cost field read-only on product forms.")
