from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale

class SakinahWebController(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        su = super(SakinahWebController, self).product(product)
        quant = http.request.env['sakinah.mutation'].sudo().search([['product_id', '=', product.id],['location_id.usage', '=', 'internal'],['location_id.warehouse_id.id', '!=', '1']])
        su.qcontext['quant'] = quant
        for q in quant:
        	print(q.__dict__)
        return su