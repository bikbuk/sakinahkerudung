from odoo import models, fields, api
from odoo.exceptions import UserError
import xmlrpclib

class SakinahAPI(models.Model):
    _name = 'sakinah.api'

    name = fields.Char('Name', required=True, index=True, copy=False)
    api_url = fields.Char('API URL', required=True)
    api_database = fields.Char('Database', required=True)
    api_email = fields.Char('E-mail', required=True)
    api_password = fields.Char('Password', required=True)
    api_active = fields.Boolean('Active')

    @api.multi
    def get_api_object(self):
        
        if self.api_active:
            try:
                odooobject = xmlrpclib.ServerProxy('%s/xmlrpc/2/object' % self.api_url)
                return odooobject
            except:
                raise UserError('Failed to connect to API database.')

    @api.multi
    def get_uid(self):
        if self.api_active:
            try:
                common = xmlrpclib.ServerProxy('%s/xmlrpc/2/common' % self.api_url)
                uid = common.authenticate(self.api_database, self.api_email, self.api_password, {})
                return uid
            except:
                raise UserError('Failed to connect to API database.')