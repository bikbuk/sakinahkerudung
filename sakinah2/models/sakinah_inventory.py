# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, AccessError
import time

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
import odoo.addons.decimal_precision as dp

class Sakinah_Users(models.Model):
    _inherit = "res.users"

    warehouses = fields.Many2many('stock.warehouse', 'res_users_stock_warehouse_rel', 'res_users_id', 'stock_warehouse_id', string='Warehouses')

class Sakinah_Warehouse(models.Model):
    _inherit = "stock.warehouse"

    users = fields.Many2many('res.users', 'res_users_stock_warehouse_rel', 'stock_warehouse_id', 'res_users_id', string='Users')
    locations = fields.One2many('stock.location', 'warehouse_id', string='Location')

class Sakinah_Location(models.Model):
    _inherit = "stock.location"

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    user_id = fields.Integer('User Id', default=lambda self: self.env.user.id)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', help="Warehouse to consider for the route selection",
        default=lambda self: self.env['stock.warehouse'].search(['&',('users.id', '=', self.env.user.id),('name','!=','Gudang Pusat')], limit=1).id,
        domain="['&',('users.id','=',user_id),('name','!=','Gudang Pusat')]")
    route_ids = fields.Many2many(
        'stock.location.route', 'stock_location_route_procurement', 'procurement_id', 'route_id', 'Preferred Routes',
        help="Preferred route to be followed by the procurement order. Usually copied from the generating document"\
        " (SO) but could be set up manually.")
    name = fields.Text('Description', default='Isi keterangan warna di sini', required=True)
    remain_qty = fields.Float('Remain Qty', compute="_compute_remaining", store=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        readonly=True, required=True, domain=[('category_id.id', '=', 1)], 
        states={'confirmed': [('readonly', False)]})

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if self.warehouse_id:
            self.location_id = self.warehouse_id.lot_stock_id.id
            self.route_ids = self.warehouse_id.route_ids.search(['&',('name','like','Procurement'),
                ('name','ilike',self.warehouse_id.name)]).ids

    @api.one
    @api.depends('product_qty','move_ids.product_uom_qty')
    def _compute_remaining(self):
        for proc in self:
            total = 0
            for move in proc.move_ids:
                if move.state == 'done':
                    total += move.product_uom_qty
            proc.remain_qty = proc.product_qty - total

    @api.multi
    def propagate_cancels(self):
        cancel_moves = self.with_context(cancel_procurement=True).filtered(lambda order: order.rule_id.action == 'move').mapped('move_ids')
        if cancel_moves:
            for cancel in cancel_moves:
                if cancel.state != 'done':
                    cancel.action_cancel()
        return self.search([('move_dest_id', 'in', cancel_moves.filtered(lambda move: move.propagate).ids)])

    @api.model
    def create(self, vals):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        new_vals = {'name': vals['name'],
                    'product_id': vals['product_id'],
                    'product_qty': vals['product_qty'],
                    'warehouse_id': vals['warehouse_id'],
                    'product_uom': vals['product_uom'],
                    'location_id': vals['location_id'],
                    'route_ids': vals['route_ids']
        }
        
        if api_uid and api_uid != self.env.uid:
            procurement_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'search', [[('name', '=', self.name)]])
            if not procurement_api and vals['name'] != 'Transit':
                api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'create', [new_vals])
        
        return super(ProcurementOrder, self).create(vals)

    @api.multi
    def cancel(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        if api_uid and api_uid != self.env.uid:
            procurement_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'search', [[('name', '=', self.name), ('create_date', '=', self.create_date), ('state', '=', 'cancel')]])
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'cancel', [procurement_api])

        propagated_procurements = self.filtered(lambda order: order.state != 'done').propagate_cancels()
        if propagated_procurements:
            propagated_procurements.cancel()
        return super(ProcurementOrder, self).cancel()

    @api.multi
    def run(self, autocommit=False):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        if api_uid and api_uid != self.env.uid:
            procurement_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'search', [[('name', '=', self.name)]])
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'run', [procurement_api])
        
        return super(ProcurementOrder, self).run(autocommit=autocommit)

    @api.multi
    def reset_to_confirmed(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        if api_uid and api_uid != self.env.uid:
            procurement_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'search', [[('name', '=', self.name)]])
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'procurement.order', 'reset_to_confirmed', [procurement_api])
        
        return self.write({'state': 'confirmed'})

class Sakinah_Mutation(models.Model):
    _name = "sakinah.mutation"
    _order = "create_date desc"

    name = fields.Char('Description', index=True, related='product_id.name')
    product_id = fields.Many2one('product.product', 'Product')
    location_id = fields.Many2one('stock.location', 'Location', index=True, required=True)
    mutation_lines = fields.One2many('sakinah.mutation.line', 'mutation_id', string='Mutation lines', domain=['&', ('create_date','<=', datetime.now().strftime('%Y-%m-%d')), ('create_date','>=', (datetime.now()-timedelta(days=30)).strftime('%Y-%m-%d')),])
    current_stock = fields.Float('Current Stock', compute='_compute_stock')

    @api.depends('product_id', 'location_id')
    def _compute_stock(self):
        for mutation in self:
            quants = self.env['stock.quant'].search([('product_id', '=', mutation.product_id.id), ('location_id', '=', mutation.location_id.id)])
            qty = 0

            for quant in quants:
                qty += quant.qty

            mutation.current_stock = qty


class Sakinah_Mutation_Line(models.Model):
    _name = "sakinah.mutation.line"
    _order = "create_date asc"

    name = fields.Char('Product', index=True, related='product_id.name')
    product_id = fields.Many2one('product.product', 'Product')
    location_id = fields.Many2one('stock.location', 'Location', index=True, required=True)
    mutation_type = fields.Selection([
        ('buy', 'Pembelian'),
        ('sell', 'Penjualan'),
        ('in', 'Barang Masuk'),
        ('out', 'Barang Keluar')
        ], string='Mutation Type', readonly=True, index=True, copy=False)
    mutation_id = fields.Many2one('sakinah.mutation', 'Mutation', required=True, domain=[('create_date', '>', datetime.now().strftime('%Y-%m-%d'))])
    product_qty = fields.Float('Quantitiy')
    qty_sum = fields.Float('Sum Stock', store=True, readonly=True)

    @api.model
    def create(self, vals):
        # TDE CLEANME: why doing this tracking on picking here ? seems weird
        quants = self.env['stock.quant'].search([('product_id', '=', vals['product_id']), ('location_id', '=', vals['location_id'])])
        location = self.env['stock.location'].search([('id', '=', vals['location_id'])])
        qty = 0

        for quant in quants:
            qty += quant.qty

        if location.usage == 'internal':
            vals['qty_sum'] = qty

        mutation = self.env['sakinah.mutation']
        mutation_id = mutation.search([('product_id', '=', vals['product_id']), ('location_id', '=', vals['location_id'])])

        if not mutation_id:
            mutation_id = mutation.sudo().create({
                'product_id': vals['product_id'],
                'location_id': vals['location_id']
                })

            vals['mutation_id'] = mutation_id.id
        else:
            vals['mutation_id'] = mutation_id.id

        return super(Sakinah_Mutation_Line, self).create(vals)


class Sakinah_Warehouse_Batch(models.Model):
    _name = "sakinah.warehouse.batch"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sakinah Warehouse Batch"
    _order = "create_date desc"

    name = fields.Char('Batch ID', required=True, index=True, copy=False, default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wait', 'Waiting for validation'),
        ('done', 'Done')
        ], string='Status', readonly=True, index=True, copy=False, default='draft')
    stock_picking = fields.One2many('stock.picking', 'parent_batch', string='Stock Picking',
        domain=[('picking_type_id.name','in',['Receipts','Finished'])])
    stock_move = fields.One2many('sakinah.stock.batch', 'parent_batch', string='Stock Picking')
    validation_count = fields.Integer('Remaining Transfer', compute='_compute_validation', store=True)
    product_plus = fields.Integer('Transfer', compute='_compute_validation', store=True)

    @api.depends('stock_picking.state', 'stock_move.plus_sum')
    def _compute_validation(self):
        for line in self:
            all_pick = 0
            done_pick = 0
            plus = 0
            for subline in line.stock_picking:
                all_pick += 1
                if subline.state == 'done':
                    done_pick += 1
            line.validation_count = all_pick - done_pick
            for subline in line.stock_move:
                plus += subline.plus_sum
            line.product_plus = plus

    @api.model
    def create(self, vals):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('sakinah.wh.batch') or '/'
        print(self.env.user)
        print(self.env.uid)
        if api_uid and api_uid != self.env.uid:
            wh_batch_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'sakinah.warehouse.batch', 'search', [[('name', '=', vals['name'])]])
            if not wh_batch_api:
                api_object.execute_kw(api.api_database, api_uid, api.api_password, 'sakinah.warehouse.batch', 'create', [vals])
        
        return super(Sakinah_Warehouse_Batch, self).create(vals)

    @api.multi
    def button_done(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        for line in self:
            count = 0
            finished = 0
            for subline in line.stock_picking:
                count += 1
                #if subline.state == 'done':
                if subline.state in ['done', 'cancel']:
                    finished += 1
            if count == finished:
                self.write({'state': 'done'})
            else:
                raise UserError(_('Tidak dapat menyelesaikan transaksi'\
                    ' jika masih ada transfer yang belum berstatus (done)'))
        if api_uid and api_uid != self.env.uid:
            wh_batch_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'sakinah.warehouse.batch', 'search', [[('name', '=', self.name)]])
            if wh_batch_api:
                api_object.execute_kw(api.api_database, api_uid, api.api_password, 'sakinah.warehouse.batch', 'button_done', [wh_batch_api])
        
        return True

    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['domain'] = "[('id', 'in', " + str(self.stock_picking.ids) + ")]"
        return result

    @api.multi
    def action_view_pack(self):
        action = self.env.ref('sakinah2.sakinah_st_batch')
        result = action.read()[0]
        result['domain'] = "[('id', 'in', " + str(self.stock_move.ids) + "),('count','!=',0)]"
        return result

class Sakinah_Stock_Batch(models.Model):
    _name = "sakinah.stock.batch"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Sakinah Stock Batch"

    name = fields.Char('Product', index=True, related='product_id.name')
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade")
    parent_batch = fields.Many2one('sakinah.warehouse.batch', string='Batch')
    stock_pack = fields.One2many('stock.pack.operation', 'child_batch', string='Stock Move', domain=[('picking_id.picking_type_id.name','in',['Receipts','Finished'])])
    count = fields.Integer('Count', compute='_compute', store=True)
    plus_sum = fields.Integer('Total Plus', compute='_compute', store=True)
    begining = fields.Integer('Begining', compute='_compute_data', store=True)
    shipped = fields.Integer('+ Shipped', compute='_compute_data', store=True)
    ending = fields.Integer('Ending =', compute='_compute_ending', store=True)
    real = fields.Integer('Real', compute='_compute_data', store=True)
    remaining = fields.Integer('In Transit', compute='_compute_ending')

    @api.depends('stock_pack.difference', 'stock_pack.state')
    def _compute(self):
        for line in self:
            count = 0
            result = 0
            for subline in line.stock_pack:
                count += 1
                if subline.state == 'done' and subline.picking_id.picking_type_id.priority not in (0, 1, 100):
                    result += subline.difference
                elif subline.difference > 0 and subline.state != 'done' and subline.picking_id.picking_type_id.priority not in (0, 1, 100):
                    result += subline.difference
            line.plus_sum = result
            line.count = count

    @api.depends('stock_pack')
    def _compute_data(self):
        for line in self:
            real = 0
            begining = 0
            shipped = 0
            for subline in line.stock_pack:
                if subline.picking_id.picking_type_id.priority == 1:
                    begining += subline.qty_done
                elif subline.picking_id.picking_type_id.priority == 100:
                    real += subline.qty_done
                elif subline.picking_id.picking_type_id.priority != 0:
                    shipped += subline.qty_done
            line.begining = begining
            line.shipped = shipped
            line.real = real

    @api.depends('stock_pack')
    def _compute_ending(self):
        for line in self:
            line.ending = line.begining - line.shipped
            line.remaining = line. ending - line.real

class Sakinah_StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    location_id = fields.Integer(related='pick_id.location_id.id')

    @api.one
    def _process(self, cancel_backorder=False):
        operations_to_delete = self.pick_id.pack_operation_ids.filtered(lambda o: o.qty_done <= 0)
        for pack in self.pick_id.pack_operation_ids - operations_to_delete:
            pack.begining_qty = pack.product_qty
            pack.product_qty = pack.qty_done

        operations_to_delete.unlink()
        self.pick_id.do_transfer()

        if cancel_backorder:
            backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', self.pick_id.id)])
            backorder_pick2 = self.env['stock.picking'].search([('warehouse_src_id', '=', self.pick_id.warehouse_src_id.id), ('warehouse_dest_id', '=', self.pick_id.warehouse_dest_id.id), ('picking_type_id.code', '=', 'internal'), ('picking_type_id.warehouse_id', '=', self.pick_id.picking_type_id.warehouse_id.id), ('state', 'not in', ['done','cancel'])])
            backorder_pick.action_cancel()
            if backorder_pick2:
                backorder_pick2.action_cancel()
            self.pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (backorder_pick.name))

        return True

    @api.multi
    def process(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        self._process()
        
        if api_uid and api_uid != self.env.uid:
            pick_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.picking', 'search', [[('name', '=', self.pick_id.name)]])
            if pick_api:
                backorder_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.backorder.confirmation', 'create', [{'pick_id': pick_api[0]}])
                api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.backorder.confirmation', 'process', [backorder_api])
        return True

    @api.multi
    def process_cancel_backorder(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()

        self._process(cancel_backorder=True)
        
        if api_uid and api_uid != self.env.uid:
            pick_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.picking', 'search', [[('name', '=', self.pick_id.name)]])
            if pick_api:
                backorder_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.backorder.confirmation', 'create', [{'pick_id': pick_api[0]}])
                api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.backorder.confirmation', 'process_cancel_backorder', [backorder_api])
        return True
class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if self.barcode:
            self.default_code = self.barcode
            

    @api.model
    def create(self, vals):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        if api_uid and api_uid != self.env.uid:
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'product.template', 'create', [vals])

        return super(ProductTemplate, self).create(vals)

class SakinahInventory(models.Model):
    _inherit = "stock.inventory"

    total_quant_value = fields.Float(string='Total Inventory Value', compute='_compute_total_value')

    @api.depends('move_ids')
    def _compute_total_value(self):
        for record in self:
            total_value = 0
            for values in record.move_ids:
                if values.adjust == 'plus':
                    total_value += values.quant_value
                elif values.adjust == 'minus':
                    total_value -= values.quant_value
            record.total_quant_value = total_value

    @api.model
    def create(self, vals):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        # TDE FIXME: context brol
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        if api_uid and api_uid != self.env.uid:
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'create', [vals])

        return super(SakinahInventory, self).create(vals)

    @api.multi
    def prepare_inventory(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        if api_uid and api_uid != self.env.uid:
            inven_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'search', [[('name', '=', self.name),('state', '=', self.state)]])
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'prepare_inventory', [inven_api])

        return super(SakinahInventory, self).prepare_inventory()

    @api.multi
    def action_cancel_draft(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        if api_uid and api_uid != self.env.uid:
            inven_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'search', [[('name', '=', self.name),('state', '=', self.state)]])
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'action_cancel_draft', [inven_api])

        self.mapped('move_ids').action_cancel()
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })

        return True

    @api.multi
    def action_done(self):
        api = self.env['sakinah.api'].search([('api_active', '=', True)])
        api_object = api.get_api_object()
        api_uid = api.get_uid()
        
        if api_uid and api_uid != self.env.uid:
            inven_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'search', [[('name', '=', self.name),('state', '=', self.state)]])

            if self.line_ids:
                for line in self.line_ids:
                    line_vals = {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'location_id': line.location_id.id,
                        'product_qty': line.product_qty,
                        'inventory_id': inven_api[0]
                    }
                    line_api = api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory.line', 'create', [line_vals])
        
            api_object.execute_kw(api.api_database, api_uid, api.api_password, 'stock.inventory', 'action_done', [inven_api])

        return super(SakinahInventory, self).action_done()
