from odoo import fields, models


class ProfitabilityTier(models.Model):
    _name = 'product.profitability.tier'
    _description = 'Profitability Tier'
    _order = 'min_margin desc, id desc'

    name = fields.Char(string='Label', required=True, translate=True)
    min_margin = fields.Float(
        string='Min Margin %', required=True,
        help="This tier applies when the margin % is greater than or equal to "
             "this value (and below the next higher tier).")
    decoration = fields.Selection(
        [('success', 'Green'), ('info', 'Blue'), ('warning', 'Amber'),
         ('danger', 'Red'), ('muted', 'Grey')],
        string='Color', default='info', required=True)
    active = fields.Boolean(default=True)
