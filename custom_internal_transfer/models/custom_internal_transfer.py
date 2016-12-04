from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from datetime import datetime

class custom_internal_transfer(models.Model):
    _name ='custom.internal.transfer'

    @api.multi
    def _employee_get(self):
        u_id = self.env.user.id
        employee_obj = self.env['hr.employee']
        employee_search = employee_obj.search([['user_id','=',u_id]])
        employee_id = employee_search.id
        # self.requisition_by = employee_id
        return employee_id

    @api.multi
    def _department_get(self):
        u_id = self.env.user.id
        employee_obj = self.env['hr.employee']
        employee_search = employee_obj.search([['user_id','=',u_id]])
        department_id = employee_search.department_id.id
        return department_id


    employee_id = fields.Many2one('hr.employee','Employee', readonly=True, store=True, default=_employee_get)
    department_id = fields.Many2one('hr.department', 'Department', readonly=True, store=True, default=_department_get)
    date_of_req = fields.Date('Requisition Date', readonly=True, store=True, default=datetime.today().date())
    requisition_items = fields.One2many('custom.internal.requisition.items','name','Requisition Item')
    state = fields.Selection([
            ('draft','Draft'),
            ('hod','HOD'),
            ('warehouse','Warehouse'),
            ('employee','Employee'),
            ('done','Done'),
            ('reject','Reject'),
        ], string='Status', default='draft',
        help=" * The 'Draft' status is used when a user starts to make a requsition for a product or products.\n"
             " * The 'HOD' HOD has to approve if there is any new requistion from his/her department.\n"
             " * The 'Warehouse' Warehouse has now the ability to deliver the product to employee.\n"
             " * The 'Done' The requisition process is done and employee has received the product or products.\n"
             " * The 'Reject' status is used when the requisition gets rejected.")

    @api.multi
    def req_send_to_hod(self):
        self.write({'state': 'hod'})

    @api.multi
    def req_approve(self):
        self.write({'state': 'warehouse'})

    @api.multi
    def req_reject(self):
        self.write({'state': 'reject'})

    @api.multi
    def req_send_to_employee(self):

        # Checking if Every Product is available in stock to deliver. If every item is available then
        # requisition can proceed
        make_move = False
        for line_items in self.requisition_items:
            if line_items.delivery_quantity <= line_items.available_quantity:
                make_move = True
            else:
                make_move = False
                break
        if make_move == True:
            # Stock Move Code
            """ Creates stock move for operation and stock move for final product to deliver.
            """
            res = {}
            Move = self.env['stock.move']
            if self.requisition_items:
                for transfer in self:
                    moves = self.env['stock.move']
                    for products in transfer.requisition_items:
                        move = Move.create({
                            'name': transfer.employee_id.name,
                            'product_id': products.product_id.id,
                            'restrict_lot_id': False,
                            'product_uom_qty': products.delivery_quantity,
                            'product_uom': products.delivery_quantity_uom.id,
                            'partner_id': 1,  # TODO: Change the test value 1 to partner_id
                            'location_id': products.source_location.id,
                            'location_dest_id': products.destination_location.id,
                        })
                        moves |= move
                        moves.action_done()
                        products.write({'move_id': move.id, 'state': 'done'})

                    res[transfer.id] = move.id
                state_change = self.write({'state': 'employee'})
            else:
                raise Warning(_('You cannot deliver without product.'))
        else:
            raise Warning(_('Delivery Quantity Cannot be more than available quantity.'))

        return res, state_change


    @api.multi
    def req_receive(self):
        # emp_obj = self.env['hr.employee'].search([['id','=',self.employee_id]])
        # for products in self.requisition_items:
        #     move = emp_obj.write({
        #         'product_id': products.product_id.id,
        #         'received_quantity': products.delivery_quantity,
        #         # 'product_uom': products.delivery_quantity_uom.id,
        #         # 'partner_id': 1,  # TODO: Change the test value 1 to partner_id
        #         # 'location_id': products.source_location.id,
        #         # 'location_dest_id': products.destination_location.id,
        #     })

        state_write = self.write({'state': 'done'})
        return state_write

    # @api.onchange('employee_id')
    # def get_partner_id(self):
    #     emp_obj = self.env['hr.employee']
    #     partner_obj = self.env['res.partner']


class custom_requistion_items(models.Model):
    _name = 'custom.internal.requisition.items'

    name = fields.Many2one('custom.internal.transfer', 'Internal Transfer Requisition')
    product_id = fields.Many2one('product.product','Product')
    req_quantity = fields.Float('Requested Quantity')
    delivery_quantity = fields.Float('Delivered Quantity')
    available_quantity = fields.Float('Available Quantity')
    delivery_quantity_uom = fields.Many2one('product.uom', 'Product UOM')
    source_location = fields.Many2one('stock.location', 'Source Location')
    destination_location = fields.Many2one('stock.location', 'Destination Location')

    @api.onchange('product_id','source_location')
    def product_qty_location_check(self):
        if self.product_id and self.source_location:
            product = self.product_id
            available_qty = product.with_context({'location':self.source_location.id}).qty_available
            self.available_quantity = available_qty

        if self.product_id:
            product_obj = self.env['product.template']
            product_uom = product_obj.search([['id','=', self.product_id.id]]).uom_id
            self.delivery_quantity_uom = product_uom



class employee_receive_product(models.Model):
    _inherit = 'hr.employee'

    employee_inventory = fields.One2many('employee.received.table','name','Employee Product/Equipment List')

class employee_received_table(models.Model):
    _name = 'employee.received.table'

    name = fields.Many2one('hr.employee', 'Employee Product/Equipment Rel')
    product_id = fields.Many2one('product.product', 'Product')
    received_qty = fields.Float('Received Quantity')
