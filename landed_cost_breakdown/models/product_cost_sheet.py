from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Cost components used across the module. Landed cost lines reuse the subset
# without 'purchase' (the base cost is never a landed cost line).
COMPONENT_SELECTION = [
    ('purchase', 'Purchase / Base Cost'),
    ('freight', 'Freight / Landed'),
    ('duty', 'Duty / Tax'),
    ('labour', 'Direct Labour'),
    ('other', 'Direct Other'),
    ('overhead', 'Overhead'),
]
COMPONENT_LABELS = dict(COMPONENT_SELECTION)


class ProductCostSheet(models.Model):
    _name = 'product.cost.sheet'
    _description = 'Product Cost Sheet'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='New', copy=False, readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id', store=True, index=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string='Currency')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('released', 'Released')],
        string='Status', default='draft', tracking=True)
    cost_method = fields.Selection(
        related='product_id.cost_method', string='Costing Method', readonly=True)
    line_ids = fields.One2many(
        'product.cost.sheet.line', 'sheet_id', string='Cost Components',
        copy=True)
    history_line_ids = fields.One2many(
        'product.cost.history.line', 'sheet_id', string='Cost History')
    layer_ids = fields.One2many(
        'product.cost.current.layer', 'sheet_id', string='Current Cost Layers')
    history_period = fields.Selection(
        [('this_month', 'This Month'), ('last_month', 'Last Month'),
         ('this_year', 'This Year'), ('last_year', 'Last Year'),
         ('all', 'All'), ('custom', 'Custom')],
        string='History Period', default='this_month')
    history_date_from = fields.Date(string='From')
    history_date_to = fields.Date(string='To')
    total_cost = fields.Monetary(
        string='Total Cost / Unit', compute='_compute_total_cost', store=True,
        currency_field='currency_id')
    current_standard_price = fields.Monetary(
        string='Current Product Cost', compute='_compute_current_price',
        currency_field='currency_id')
    variance = fields.Monetary(
        string='Variance vs Product Cost', compute='_compute_current_price',
        currency_field='currency_id',
        help="Difference between this sheet's total and the product's current cost.")
    released_by = fields.Many2one('res.users', string='Released By', readonly=True, copy=False)
    released_on = fields.Datetime(string='Released On', readonly=True, copy=False)
    note = fields.Text(string='Notes')

    @api.depends('line_ids.amount', 'line_ids.hidden')
    def _compute_total_cost(self):
        for sheet in self:
            sheet.total_cost = sum(
                line.amount for line in sheet.line_ids if not line.hidden)

    @api.depends('product_id', 'company_id', 'total_cost')
    def _compute_current_price(self):
        for sheet in self:
            price = sheet.product_id.with_company(sheet.company_id).standard_price
            sheet.current_standard_price = price
            sheet.variance = sheet.total_cost - price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'product.cost.sheet') or 'New'
        return super().create(vals_list)

    def action_build_breakdown(self):
        """(Re)build the breakdown lines from the product's current data:
        the base cost plus categorized landed-cost contributions."""
        for sheet in self:
            if sheet.state == 'released':
                raise UserError(_("A released cost sheet cannot be rebuilt. Create a new one."))
            sheet._build_lines()
            sheet._build_history()
            sheet._build_current_layers()
        return True

    def _build_current_layers(self):
        """Show how the current cost is calculated: the units in stock (remaining
        layers), each layer's unit cost, and their weighted average = current cost."""
        self.ensure_one()
        product = self.product_id
        company = self.company_id
        moves = self.env['stock.move'].sudo().search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('company_id', '=', company.id),
        ], limit=5000)
        cmds = []
        for move in moves.filtered(lambda m: m._is_in() and m.remaining_qty).sorted('date'):
            rq = move.remaining_qty
            doc = (move.purchase_line_id.order_id.name if move.purchase_line_id
                   else (move.picking_id.name or move.reference or ''))
            cmds.append((0, 0, {
                'date': move.date,
                'document': doc,
                'quantity': rq,
                'unit_cost': (move.remaining_value / rq) if rq else 0.0,
                'value': move.remaining_value,
            }))
        self.write({'layer_ids': [(5, 0, 0)] + cmds})

    def action_refresh_history(self):
        """Rebuild the Cost History for the chosen period (Apply button)."""
        for sheet in self:
            sheet._build_history()
        return True

    def _history_date_range(self):
        """Return (date_from, date_to) for the selected history period."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        period = self.history_period
        if period == 'this_month':
            return today.replace(day=1), today
        if period == 'last_month':
            first_this = today.replace(day=1)
            last_prev = first_this - relativedelta(days=1)
            return last_prev.replace(day=1), last_prev
        if period == 'this_year':
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        if period == 'last_year':
            y = today.year - 1
            return date(y, 1, 1), date(y, 12, 31)
        if period == 'custom':
            return self.history_date_from, self.history_date_to
        return False, False  # all

    def _build_history(self):
        """One row per past receipt: base cost + landed cost = batch cost (per
        unit), so you can see what each historical purchase actually cost."""
        self.ensure_one()
        product = self.product_id
        company = self.company_id
        Adj = self.env['stock.valuation.adjustment.lines'].sudo()
        date_from, date_to = self._history_date_range()

        moves = self.env['stock.move'].sudo().search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('company_id', '=', company.id),
        ], limit=5000)

        cmds = []
        for move in moves.filtered(lambda m: m._is_in()).sorted('date'):
            mdate = move.date.date() if move.date else False
            if date_from and mdate and mdate < date_from:
                continue
            if date_to and mdate and mdate > date_to:
                continue
            qty = move._get_valued_qty() or move.quantity
            if not qty:
                continue
            landed = sum(Adj.search([
                ('move_id', '=', move.id), ('cost_id.state', '=', 'done'),
            ]).mapped('additional_landed_cost'))
            doc = (move.purchase_line_id.order_id.name if move.purchase_line_id
                   else (move.picking_id.name or move.reference or ''))
            cmds.append((0, 0, {
                'date': move.date,
                'document': doc,
                'quantity': qty,
                'base_cost': (move.value - landed) / qty,
                'landed_cost': landed / qty,
                'batch_cost': move.value / qty,
            }))

        self.write({'history_line_ids': [(5, 0, 0)] + cmds})

    def _build_lines(self):
        self.ensure_one()
        # Remember which lines the user hid, so a rebuild keeps them hidden.
        hidden_keys = {(l.component, l.name) for l in self.line_ids if l.hidden}
        product = self.product_id
        company = self.company_id
        std_price = product.with_company(company).standard_price
        in_cost = product.cost_method in ('fifo', 'average')
        Adj = self.env['stock.valuation.adjustment.lines'].sudo()

        moves = self.env['stock.move'].sudo().search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('company_id', '=', company.id),
        ], limit=2000)
        in_moves = moves.filtered(lambda m: m._is_in())
        # Breakdown reflects the MOST RECENT receipt (latest PO + its landed
        # costs). Older receipts are visible in the Cost History tab.
        rem_moves = in_moves.sorted(lambda m: (m.date, m.id), reverse=True)[:1]

        total_qty = 0.0
        base_total = 0.0
        landed_groups = {}  # (cost_id, component) -> {'cost', 'component', 'value'}
        last_po = self.env['purchase.order']
        for move in rem_moves:
            mq = move._get_valued_qty() or move.quantity
            qty = mq
            if not mq or not qty:
                continue
            ratio = qty / mq
            adj = Adj.search([('move_id', '=', move.id), ('cost_id.state', '=', 'done')])
            move_landed = 0.0
            for al in adj:
                comp = al.cost_line_id.cost_component or 'freight'
                key = (al.cost_id.id, comp)
                data = landed_groups.setdefault(key, {
                    'cost': al.cost_id, 'component': comp, 'value': 0.0, 'desc': ''})
                if not data['desc']:
                    data['desc'] = (al.cost_line_id.product_id.display_name
                                    or al.cost_line_id.name or al.cost_id.name)
                data['value'] += al.additional_landed_cost * ratio
                move_landed += al.additional_landed_cost
            # purchase portion = fully-loaded move value minus its landed costs
            base_total += (move.value - move_landed) * ratio
            total_qty += qty
            if move.purchase_line_id:
                last_po = move.purchase_line_id.order_id

        base_desc = _('Purchase Cost')

        line_cmds = [(0, 0, {
            'component': 'purchase',
            'name': base_desc,
            'amount': (base_total / total_qty) if total_qty else std_price,
            'source_ref': ('purchase.order,%s' % last_po.id) if last_po else False,
            'included_in_cost': True,
            'hidden': ('purchase', base_desc) in hidden_keys,
        })]
        for data in sorted(landed_groups.values(),
                           key=lambda d: (d['cost'].date or fields.Date.today(), d['cost'].id)):
            desc = data['desc'] or COMPONENT_LABELS.get(data['component'], data['component'])
            line_cmds.append((0, 0, {
                'component': data['component'],
                'name': desc,
                'amount': (data['value'] / total_qty) if total_qty else 0.0,
                'source_ref': 'stock.landed.cost,%s' % data['cost'].id,
                'included_in_cost': in_cost,
                'hidden': (data['component'], desc) in hidden_keys,
            }))

        self.write({'line_ids': [(5, 0, 0)] + line_cmds})

    def action_release(self):
        """Write this sheet's total cost back to the product's cost, logged."""
        self.ensure_one()
        if not self.env.user.has_group('landed_cost_breakdown.group_cost_manager'):
            raise UserError(_("Only a Cost Manager can release a cost update."))
        if self.state == 'released':
            raise UserError(_("This cost sheet is already released."))
        if not self.line_ids:
            raise UserError(_("Build the cost breakdown before releasing."))
        product = self.product_id.with_company(self.company_id)
        old_price = product.standard_price
        product.write({'standard_price': self.total_cost})
        self.write({
            'state': 'released',
            'released_by': self.env.user.id,
            'released_on': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "Cost released: product cost updated from %(old)s to %(new)s.",
            old=old_price, new=self.total_cost))
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'released_by': False, 'released_on': False})
        return True

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('landed_cost_breakdown.action_report_cost_sheet').report_action(self)


class ProductCostSheetLine(models.Model):
    _name = 'product.cost.sheet.line'
    _description = 'Product Cost Sheet Line'
    _order = 'sequence, id'

    sheet_id = fields.Many2one(
        'product.cost.sheet', string='Cost Sheet', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    component = fields.Selection(
        COMPONENT_SELECTION, string='Component', required=True, default='other')
    name = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount / Unit', currency_field='currency_id')
    currency_id = fields.Many2one(related='sheet_id.currency_id', string='Currency')
    source_ref = fields.Reference(
        selection=[
            ('stock.landed.cost', 'Landed Cost'),
            ('account.move', 'Journal Entry / Bill'),
            ('purchase.order', 'Purchase Order'),
        ],
        string='Source Document')
    hidden = fields.Boolean(
        string='Hide',
        help="Hide this line from the breakdown total and the printed PDF.")
    included_in_cost = fields.Boolean(
        string='In Product Cost',
        help="Whether this amount is already included in the product's stored cost "
             "(true for FIFO/Average landed costs).")


class ProductCostHistoryLine(models.Model):
    _name = 'product.cost.history.line'
    _description = 'Product Cost History Line'
    _order = 'date, id'

    sheet_id = fields.Many2one(
        'product.cost.sheet', string='Cost Sheet', required=True, ondelete='cascade')
    date = fields.Datetime(string='Date')
    document = fields.Char(string='Purchase Order')
    quantity = fields.Float(string='Qty')
    base_cost = fields.Monetary(string='Base Cost', currency_field='currency_id')
    landed_cost = fields.Monetary(string='Landed Cost', currency_field='currency_id')
    batch_cost = fields.Monetary(string='Batch Cost', currency_field='currency_id')
    currency_id = fields.Many2one(related='sheet_id.currency_id', string='Currency')


class ProductCostCurrentLayer(models.Model):
    _name = 'product.cost.current.layer'
    _description = 'Product Cost Current Layer'
    _order = 'date, id'

    sheet_id = fields.Many2one(
        'product.cost.sheet', string='Cost Sheet', required=True, ondelete='cascade')
    date = fields.Datetime(string='Received')
    document = fields.Char(string='Purchase Order')
    quantity = fields.Float(string='Qty on Hand')
    unit_cost = fields.Monetary(string='Unit Cost', currency_field='currency_id')
    value = fields.Monetary(string='Value', currency_field='currency_id')
    currency_id = fields.Many2one(related='sheet_id.currency_id', string='Currency')
