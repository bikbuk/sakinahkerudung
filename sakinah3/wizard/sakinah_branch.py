from odoo import api, fields, models


class SakinahBranch(models.TransientModel):
    _name = 'sakinah.branch'
    _description = 'Branch Creating Wizard'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", size=5, required=True)

    @api.multi
    def start(self):

        account = self.create_account()
        user = self.create_user()
        wh = self.create_warehouse(user.id)
        self.write_location(wh.id)
        self.stock_pick_type_priority(wh.id)

        journal = self.create_journal(account.id, user.id)
        employee = self.create_employee(user.id)
        pos_conf = self.create_pos_config(journal.id)

        loc_route = self.create_location_route(wh.id)
        loc_path = self.create_location_path(loc_route.id)
        proc_rule = self.create_procurement_rule(wh.id, loc_route.id)

        return True

    @api.multi
    def create_account(self):
        account_dict = {
            'name': self.name,
            'user_type_id': self.env.ref('account.data_account_type_liquidity').id
        }
        
        account = self.env['account.account']
        account_list = account.search([('user_type_id', '=', self.env.ref('account.data_account_type_liquidity').id)])

        for acc in account_list:
            if '1015' in acc.code:
                code = str(int(acc.code)+1)
                check_account = account.search([('code', '=', code)])

                if not check_account:
                    account_dict['code'] = code

        new_account = account.create(account_dict)

        return new_account

    @api.multi
    def create_user(self):
        
        user_dict = {
            'name': self.name,
            'login': self.name.lower()+"@sakinahkerudung.com",
            'email': self.name.lower()+"@sakinahkerudung.com",
            'password': 'go50cabang',
            'signature': ">-- Branch "+self.name+" of Sakinah Kerudung",
            'notify_email': 'always',
            'company_id': self.env.ref('base.main_company').id,
            'parent_id': self.env.ref('base.main_partner').id,
            'groups_id': [(6,0, [self.env.ref('sakinah2.group_sakinah_shop').id, self.env.ref('base.group_user').id])],
        }

        new_user = self.env['res.users'].create(user_dict)

        return new_user

    @api.multi
    def create_warehouse(self, uid):
        wh_dict = {
            'name': self.name,
            'code': self.code,
            'users': [(6,0, [1, uid])],
        }

        new_warehouse = self.env['stock.warehouse'].create(wh_dict)

        return new_warehouse

    

    @api.multi
    def create_journal(self, acc_id, uid):
        journal_dict = {
            'name': self.name,
            'type': 'cash',
            'code': self.code,
            'default_debit_account_id': acc_id,
            'default_credit_account_id': acc_id,
            'journal_user': True,
            'amount_authorized_diff': '50000',
            'users': [(6,0, [uid])],
        }

        new_journal = self.env['account.journal'].create(journal_dict)

        return new_journal

    @api.multi
    def create_employee(self, uid):
        employee_dict = {
            'name': self.name,
            'user_id': uid,
        }

        return self.env['hr.employee'].create(employee_dict)

    @api.multi
    def write_location(self, wh_id):
        location = self.env['stock.location'].search([('location_id.name', '=', self.code)])

        ext_dict = {
            'name': 'loc_'+self.name.lower(),
            'module': 'sakinah2',
            'model': 'stock.location',
            'res_id': location.id,
        }
        if location:
            model_data = self.env['ir.model.data'].create(ext_dict)

            return location.write({'warehouse_id': wh_id})

    @api.multi
    def stock_pick_type_priority(self, wh_id):
        priority = 0
        pick_type = self.env['stock.picking.type']

        current_pick_type = pick_type.search([('name', '=', 'Receipts'), ('warehouse_id.id', '=', wh_id)])
        pick_type_list = pick_type.search([('name', '=', 'Receipts'), ('priority', '!=', '0')])
        
        ext_dict = {
            'name': 'pick_'+self.name.lower(),
            'module': 'sakinah2',
            'model': 'stock.picking.type',
            'res_id': current_pick_type.id,
        }
        
        if current_pick_type:
            model_data = self.env['ir.model.data'].create(ext_dict)
            
            for pick in pick_type_list:
                check_pick_type = pick_type.search([('priority', '=', pick.priority+1)])
                print(check_pick_type)
                if not check_pick_type:
                    priority = pick.priority+1
            print(priority)
            return current_pick_type.write({'priority': priority})

    @api.multi
    def create_pos_config(self, journal_id):
        pos_config_dict = {
            'name': self.name,
            'journal_id': self.env.ref('point_of_sale.pos_sale_journal').id,
            'journal_ids': [(6,0, [journal_id])],
            'iface_vkeyboard': True,
            'iface_invoicing': True,
            'iface_precompute_cash': True,
            'iface_print_auto': True,
            'iface_print_via_proxy': True,
            'iface_scan_via_proxy': True,
            'cash_control': True,
        }

        location = self.env.ref('sakinah2.loc_'+self.name.lower())

        pos_config_dict['stock_location_id'] = location.id

        return self.env['pos.config'].create(pos_config_dict)


    @api.multi
    def create_location_route(self, wh_id):
        location_route_dict = {
            'name': self.name+': Procurement',
            'product_selectable': False,
            'warehouse_ids': [(6,0, [wh_id])],
        }

        new_location_route = self.env['stock.location.route'].create(location_route_dict)

        return new_location_route


    @api.multi
    def create_location_path(self, route_id):
        loc_id = self.env.ref('sakinah2.loc_'+self.name.lower()).id
        transit = self.env.ref('sakinah2.location_transit').id
        pick_type_id = self.env.ref('sakinah2.pick_'+self.name.lower()).id

        location_path_dict = {
            'name': 'Transit',
            'auto': 'manual',
            'location_dest_id': loc_id,
            'location_from_id': transit,
            'route_id': route_id,
            'picking_type_id': pick_type_id,
        }

        new_location_path = self.env['stock.location.path'].create(location_path_dict)

        return new_location_path

    @api.multi
    def create_procurement_rule(self, wh_id, route_id):
        loc_id = self.env.ref('sakinah2.loc_'+self.name.lower()).id
        transit = self.env.ref('sakinah2.location_transit').id
        packing = self.env.ref('sakinah2.location_packing').id
        pick_type_id1 = self.env.ref('sakinah2.pick_'+self.name.lower()).id
        pick_type_id2 = self.env['stock.picking.type'].search([('name', '=', "Internal Transfers"), ('warehouse_id.id', '=', wh_id)])

        procurement_rule_dict1 = {
            'name': 'Transit',
            'action': 'move',
            'location_id': loc_id,
            'location_src_id': transit,
            'procure_method': 'make_to_order',
            'route_id': route_id,
            'picking_type_id': pick_type_id1,
        }

        procurement_rule_dict2 = {
            'name': self.name,
            'action': 'move',
            'location_id': transit,
            'location_src_id': packing,
            'procure_method': 'make_to_stock',
            'route_id': route_id,
            'picking_type_id': pick_type_id2.id,
        }

        proc_rule1 = self.env['procurement.rule'].create(procurement_rule_dict1)
        proc_rule1 = self.env['procurement.rule'].create(procurement_rule_dict2)

        return True