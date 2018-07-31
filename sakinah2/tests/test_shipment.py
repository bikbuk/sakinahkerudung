from odoo.addons.stock.tests.common import TestStockCommon

class TestStockFlow(TestStockCommon):

    def _create_custom_picking(self, batch, loc_id, loc_dest_id, picktype):
        Loc = self.env['stock.location']
        PickType = self.env['stock.picking.type']

        picking = self.PickingObj.create({
            'parent_batch': batch,
            'location_id': Loc.search([('id', '=', loc_id)]).id,
            'location_dest_id': Loc.search([('id', '=', loc_dest_id)]).id,
            'picking_type_id': PickType.search([('id', '=', picktype)]).id,
            })

        return picking

    def _create_custom_move(self, def_code, pick_id, loc_id, loc_dest_id, qty):
        Product = self.env['product.product'].search([('default_code', '=', def_code)])

        move = self.MoveObj.create({
                'name': Product.name,
                'product_id': Product.id,
                'product_uom_qty': qty,
                'product_uom': Product.uom_id.id,
                'picking_id': pick_id,
                'location_id': loc_id,
                'location_dest_id': loc_dest_id})

        return move

    def _set_qty_pack(self, picking):
        for pack in picking.pack_operation_product_ids:
            self.StockPackObj.search([('product_id', '=', pack.product_id.id), ('picking_id', '=', picking.id)]).write({'product_qty': 10.0})


    def test_00_picking_create_and_transfer_quantity(self):

        val = {'name': 'New'}

        self.batch = self.env['sakinah.warehouse.batch'].create(val)

        self.picking_gudang_riung = self._create_custom_picking(self.batch.id,97,96,11)
        self.riung_move_1 = self._create_custom_move('0051',self.picking_gudang_riung.id,self.picking_gudang_riung.location_id.id,self.picking_gudang_riung.location_dest_id.id, 10)
        self.riung_move_2 = self._create_custom_move('0055',self.picking_gudang_riung.id,self.picking_gudang_riung.location_id.id,self.picking_gudang_riung.location_dest_id.id, 10)
        self.riung_move_3 = self._create_custom_move('0056',self.picking_gudang_riung.id,self.picking_gudang_riung.location_id.id,self.picking_gudang_riung.location_dest_id.id, 10)
        
        self.assertEqual(self.picking_gudang_riung.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_riung.warehouse_src_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_riung.warehouse_dest_id.name, "Riung")
        self.assertEqual(self.picking_gudang_riung.location_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_riung.location_dest_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_riung.state, 'draft')

        self.picking_gudang_riung.action_confirm()

        self.assertEqual(self.picking_gudang_riung.state, 'confirmed')

        self.picking_gudang_riung.force_assign()

        self.assertEqual(self.picking_gudang_riung.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_riung)

        self.picking_gudang_riung.do_transfer()

        self.assertEqual(self.picking_gudang_riung.state, 'done')

        self.picking_gudang_jtngr = self._create_custom_picking(self.batch.id,97,96,26)
        self.jtngr_move_1 = self._create_custom_move('0051',self.picking_gudang_jtngr.id,self.picking_gudang_jtngr.location_id.id,self.picking_gudang_jtngr.location_dest_id.id, 10)
        self.jtngr_move_2 = self._create_custom_move('0055',self.picking_gudang_jtngr.id,self.picking_gudang_jtngr.location_id.id,self.picking_gudang_jtngr.location_dest_id.id, 10)
        self.jtngr_move_3 = self._create_custom_move('0056',self.picking_gudang_jtngr.id,self.picking_gudang_jtngr.location_id.id,self.picking_gudang_jtngr.location_dest_id.id, 10)
        
        self.assertEqual(self.picking_gudang_jtngr.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_jtngr.warehouse_src_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_jtngr.warehouse_dest_id.name, "Jatinangor")
        self.assertEqual(self.picking_gudang_jtngr.location_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_jtngr.location_dest_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_jtngr.state, 'draft')

        self.picking_gudang_jtngr.action_confirm()

        self.assertEqual(self.picking_gudang_jtngr.state, 'confirmed')

        self.picking_gudang_jtngr.force_assign()

        self.assertEqual(self.picking_gudang_jtngr.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_jtngr)

        self.picking_gudang_jtngr.do_transfer()

        self.assertEqual(self.picking_gudang_jtngr.state, 'done')

        self.picking_gudang_grlng = self._create_custom_picking(self.batch.id,97,96,71)
        self.grlng_move_1 = self._create_custom_move('0051',self.picking_gudang_grlng.id,self.picking_gudang_grlng.location_id.id,self.picking_gudang_grlng.location_dest_id.id, 10)
        self.grlng_move_2 = self._create_custom_move('0055',self.picking_gudang_grlng.id,self.picking_gudang_grlng.location_id.id,self.picking_gudang_grlng.location_dest_id.id, 10)
        self.grlng_move_3 = self._create_custom_move('0056',self.picking_gudang_grlng.id,self.picking_gudang_grlng.location_id.id,self.picking_gudang_grlng.location_dest_id.id, 10)

        self.assertEqual(self.picking_gudang_grlng.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_grlng.warehouse_src_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_grlng.warehouse_dest_id.name, "Gerlong")
        self.assertEqual(self.picking_gudang_grlng.location_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_grlng.location_dest_id.warehouse_id.name, "Gudang Pusat")
        self.assertEqual(self.picking_gudang_grlng.state, 'draft')

        self.picking_gudang_grlng.action_confirm()

        self.assertEqual(self.picking_gudang_grlng.state, 'confirmed')

        self.picking_gudang_grlng.force_assign()

        self.assertEqual(self.picking_gudang_grlng.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_grlng)

        self.picking_gudang_grlng.do_transfer()

        self.assertEqual(self.picking_gudang_grlng.state, 'done')

        print("TEST 1 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 1 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 1 SUCC SUCC SUCC SUCC SUCCESS")

    def test_10_picking_create_and_transfer_quantity2(self):

        self.test_00_picking_create_and_transfer_quantity()

        self.picking_gudang_riung2 = self.PickingObj.search([('origin', '=', self.picking_gudang_riung.name)])

        self.assertEqual(self.picking_gudang_riung2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_riung2.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_riung2)

        self.picking_gudang_riung2.do_transfer()

        self.assertEqual(self.picking_gudang_riung2.state, 'done')

        self.picking_gudang_jtngr2 = self.PickingObj.search([('origin', '=', self.picking_gudang_jtngr.name)])

        self.assertEqual(self.picking_gudang_jtngr2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_jtngr2.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_jtngr2)

        self.picking_gudang_jtngr2.do_transfer()

        self.assertEqual(self.picking_gudang_jtngr2.state, 'done')

        self.picking_gudang_grlng2 = self.PickingObj.search([('origin', '=', self.picking_gudang_grlng.name)])

        self.assertEqual(self.picking_gudang_grlng2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_grlng2.state, 'assigned')

        self._set_qty_pack(self.picking_gudang_grlng2)

        self.picking_gudang_grlng2.do_transfer()

        self.assertEqual(self.picking_gudang_grlng2.state, 'done')

        print("TEST 2 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 2 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 2 SUCC SUCC SUCC SUCC SUCCESS")

    def test_20_picking_create_and_transfer_quantity3(self):

        self.test_00_picking_create_and_transfer_quantity()

        self.picking_gudang_riung2 = self.PickingObj.search([('origin', '=', self.picking_gudang_riung.name)])

        self.assertEqual(self.picking_gudang_riung2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_riung2.state, 'assigned')

        self.riung2_pack_1 = self.StockPackObj.search([('product_id', '=', self.riung_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        self.riung2_pack_2 = self.StockPackObj.search([('product_id', '=', self.riung_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        self.riung2_pack_3 = self.StockPackObj.search([('product_id', '=', self.riung_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        
        self.riung2_pack_1.write({'product_qty': 9.0})
        self.riung2_pack_2.write({'product_qty': 11.0})
        self.riung2_pack_3.write({'product_qty': 9.0})

        self.picking_gudang_jtngr2 = self.PickingObj.search([('origin', '=', self.picking_gudang_jtngr.name)])

        self.assertEqual(self.picking_gudang_jtngr2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_jtngr2.state, 'assigned')

        self.jtngr2_pack_1 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        self.jtngr2_pack_2 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        self.jtngr2_pack_3 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        
        self.jtngr2_pack_1.write({'product_qty': 12.0})
        self.jtngr2_pack_2.write({'product_qty': 10.0})
        self.jtngr2_pack_3.write({'product_qty': 11.0})
        
        self.picking_gudang_grlng2 = self.PickingObj.search([('origin', '=', self.picking_gudang_grlng.name)])

        self.assertEqual(self.picking_gudang_grlng2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_grlng2.state, 'assigned')

        self.grlng2_pack_1 = self.StockPackObj.search([('product_id', '=', self.grlng_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])
        self.grlng2_pack_2 = self.StockPackObj.search([('product_id', '=', self.grlng_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])
        self.grlng2_pack_3 = self.StockPackObj.search([('product_id', '=', self.grlng_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])        

        self.grlng2_pack_1.write({'product_qty': 9.0})
        self.grlng2_pack_2.write({'product_qty': 9.0})
        self.grlng2_pack_3.write({'product_qty': 10.0})

        print("TEST 3 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 3 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 3 SUCC SUCC SUCC SUCC SUCCESS")


    def test_30_picking_create_and_transfer_quantity4(self):

        self.test_00_picking_create_and_transfer_quantity()

        self.picking_gudang_riung2 = self.PickingObj.search([('origin', '=', self.picking_gudang_riung.name)])

        self.assertEqual(self.picking_gudang_riung2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_riung2.state, 'assigned')

        self.riung2_pack_1 = self.StockPackObj.search([('product_id', '=', self.riung_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        self.riung2_pack_2 = self.StockPackObj.search([('product_id', '=', self.riung_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        self.riung2_pack_3 = self.StockPackObj.search([('product_id', '=', self.riung_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_riung2.id)])
        
        self.riung2_pack_1.write({'product_qty': 9.0})
        self.riung2_pack_2.write({'product_qty': 10.0})
        self.riung2_pack_3.write({'product_qty': 11.0})

        self.picking_gudang_jtngr2 = self.PickingObj.search([('origin', '=', self.picking_gudang_jtngr.name)])

        self.assertEqual(self.picking_gudang_jtngr2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_jtngr2.state, 'assigned')

        self.jtngr2_pack_1 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        self.jtngr2_pack_2 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        self.jtngr2_pack_3 = self.StockPackObj.search([('product_id', '=', self.jtngr_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_jtngr2.id)])
        
        self.jtngr2_pack_1.write({'product_qty': 10.0})
        self.jtngr2_pack_2.write({'product_qty': 11.0})
        self.jtngr2_pack_3.write({'product_qty': 9.0})
        
        self.picking_gudang_grlng2 = self.PickingObj.search([('origin', '=', self.picking_gudang_grlng.name)])

        self.assertEqual(self.picking_gudang_grlng2.parent_batch.id, self.batch.id)
        self.assertEqual(self.picking_gudang_grlng2.state, 'assigned')

        self.grlng2_pack_1 = self.StockPackObj.search([('product_id', '=', self.grlng_move_1.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])
        self.grlng2_pack_2 = self.StockPackObj.search([('product_id', '=', self.grlng_move_2.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])
        self.grlng2_pack_3 = self.StockPackObj.search([('product_id', '=', self.grlng_move_3.product_id.id), ('picking_id', '=', self.picking_gudang_grlng2.id)])        

        self.grlng2_pack_1.write({'product_qty': 11.0})
        self.grlng2_pack_2.write({'product_qty': 9.0})
        self.grlng2_pack_3.write({'product_qty': 10.0})

        print("TEST 4 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 4 SUCC SUCC SUCC SUCC SUCCESS")
        print("TEST 4 SUCC SUCC SUCC SUCC SUCCESS")
