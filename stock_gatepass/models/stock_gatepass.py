from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class comp_license_type(models.Model):
    _name = 'comp.license.type'

    name = fields.Char('Business Type')

class stock_gatepass(models.Model):
    _name = 'stock.gatepass'
    _inherit = ['mail.thread']

    customer = fields.Many2one('res.partner', 'Customer', required='True')
    address_id = fields.Many2one('res.partner', 'Address')
    date = fields.Date('Date')
    challan_no = fields.Many2many('stock.picking', 'gatepass_stock_picking_rel', 'gatepass_ids', 'stock_picking_ids', 'Challan No.', required='True',)
    vehicle_no = fields.Char('Vehicle No.')
    gp_no = fields.Char(string='GP No.', readonly=True)
    stock_picking_lines = fields.One2many('stock.picking.lines', 'name', 'Stock Picking Lines')
    categ_id = fields.Many2one('product.category','Product Category', help="Select category for the product")
    categ_short_id = fields.Many2one('product.category.short','Category Type', required=True, help="Select type for the category")
    comp_type = fields.Many2one('comp.license.type', 'Deal Type',)
    state = fields.Selection([
            ('draft','Draft'),
            ('done','Done'),
        ], string='State',)

    pi_generate = fields.Text('PI Numbers', compute='pi_number_generate', store=True)

    _defaults = {
        'address_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['delivery'])['delivery'],
        'state': 'draft'
    }

    #MANY2MANY FILTER
    # @api.multi
    # def get_default_challan_ids(self):
    #     # self.env.cr.execute('select stock_picking_ids from gatepass_stock_picking_rel')
    #     # self.test_text = list(self.env.cr.fetchall())
    #
    #     query = """ SELECT stock_picking_ids
    #                 FROM gatepass_stock_picking_rel"""
    #     self._cr.execute(query, (self.id,))
    #     return [row[0] for row in self._cr.fetchall()]
    #
    #
    # _defaults = {
    #     'test_text': get_default_challan_ids
    # }



    @api.multi
    def gatepass_done(self):
        return self.write({'state': 'done'})

    @api.v7
    def create(self, cr, uid, vals, context=None):
        vals['gp_no'] = self.pool.get('ir.sequence').get(cr, uid,'stock.gatepass')
        return super(stock_gatepass, self).create(cr, uid, vals, context=context)

    @api.multi
    @api.onchange('challan_no')
    def challan_no_change(self):

        challan = self.challan_no
        products = []
        products_qty = []
        seq_start = 1

        for challan_obj in challan:
            for i in challan_obj:
                move_lines = i.move_lines
                for moves in move_lines:
                    added = None
                    for items in products:
                        if items[2]['product_id'] == moves.product_id.id:
                            items[2]['quantity'] += moves.product_uom_qty
                            items[2]['ctn_bg_roll'] += moves.unit_box
                            added = True
                    if added:
                        continue
                    else:
                        products.append((0, 0, {'product_id':moves.product_id.id,
                                                'quantity':moves.product_uom_qty,
                                                # 'challan_no':i.id,
                                                'ctn_bg_roll':moves.unit_box,
                                                'sl_no':seq_start}))


                    # products.append((0, 0, {'product_id':moves.product_id.id,
                    #                             'quantity':moves.product_uom_qty,
                    #                             'challan_no':i.id,
                    #                             'sl_no':seq_start}))
                    seq_start += 1

        self.stock_picking_lines = products


    @api.one
    @api.depends('challan_no')
    def pi_number_generate(self):
        pi_list = ''
        if self.challan_no:
            for i in self.challan_no:
                if i.pi_number:
                    pi_list = pi_list+', '+i.pi_number
                else:
                    raise Warning('There is no PI number defined for this or one of the challan in the list')
        self.pi_generate = pi_list[1:]


    def onchange_customer_in_gp(self, cr, uid, ids, part, context=None):
        if not part:
            return {'value': {'address_id': False}}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])

        val = {
            'address_id': addr['delivery'],
        }

        return {'value': val}


class stock_picking_lines(models.Model):
    _name = 'stock.picking.lines'

    name = fields.Many2one('stock.gatepass', 'Name')
    challan_no = fields.Many2one('stock.picking', 'Challan No.')
    sl_no = fields.Integer('SL No.')
    product_id = fields.Many2one('product.product', 'Product', required=True, readonly=True)
    description = fields.Char('Description')
    ctn_bg_roll = fields.Char('CTN/Bag/Roll')
    quantity = fields.Integer('Quantity')
    remarks = fields.Text('Remarks')

class product_category_short(models.Model):
    _name = 'product.category.short'

    name = fields.Char('Type Name')

