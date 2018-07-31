# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from lxml import etree
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.addons.account.wizard.pos_box import CashBox          

class Sakinah_Users(models.Model):
    _inherit = "res.users"

    journal_id = fields.Many2one('account.journal', string='Journal')

class Sakinah_Accounts(models.Model):
    _inherit = "account.journal"

    users = fields.One2many('res.users', 'journal_id', string='User')

class Sakinah_POS(models.Model):
    _inherit = "pos.session"

    @api.multi
    def action_view_payment(self):
        uid = self.env.uid

        context = self._context
        
        receive = self.env['account.payment'].search([('payment_type', '=', 'transfer'), ('state', '=', 'saved'), ('destination_journal_id.users', '=', uid)], order='create_date desc', limit=1)
        sent = self.env['account.payment'].search([('payment_type', '=', 'transfer'), ('state', '=', 'saved'), ('journal_id.users', '=', uid)], order='create_date desc', limit=1)
        
        action = {
            'name': _('Payments'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'view_id': self.env.ref('account.view_account_payment_form').id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
            }

        if receive:
            action['res_id'] = receive.id

        elif sent:
            action['res_id'] = sent.id

        return action


    @api.multi
    def action_pos_session_closing_control(self):
        for session in self:
            payment = session.env['account.payment'].search([('pos_session', '=', session.id),('state', 'in', ['draft','saved'])])
            if payment:
                raise UserError(_('Tidak bisa memproses transaksi, masih ada transfer yang belum dikonfirmasi oleh penerima.'))
        return super(Sakinah_POS, self).action_pos_session_closing_control()

class Sakinah_POS_Order(models.Model):
    _inherit = "pos.order"

    @api.multi
    def send_invoice(self, order):
        mail_pool = self.env['mail.mail']

        body_html = "<h2 align='center'>Invoice</h2>"
        body_html += "<table align='center'>"
        body_html += "<tr><td>Date : %s</td></tr>" %(order.date_order)
        body_html += "<tr><td>Customer : %s</td></tr>" %(order.partner_id.name)
        body_html += "<tr></tr>"
        body_html += "<tr><td>Product list</td></tr>"
        for line in order.lines:
            body_html += "<tr><td>%s x %s</td><td align='right'>%s</td></tr>" %(int(line.qty), line.product_id.name, line.price_subtotal)
        body_html += "<tr><td><b>Total</td><td align='right'><b>%s</td></tr></table>" %(order.amount_total)

        values={}

        values.update({'subject': 'Sakinah Kerudung Invoice'})
        values.update({'email_to': order.partner_id.email})
        values.update({'body_html': body_html})

        msg_id = mail_pool.create(values)

        if msg_id:

            msg_id.send()
            print('Send Ok')

    @api.model
    def _process_order(self, pos_order):
        prec_acc = self.env['decimal.precision'].precision_get('Account')
        pos_session = self.env['pos.session'].browse(pos_order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            pos_order['pos_session_id'] = self._get_valid_session(pos_order).id
        order = self.create(self._order_fields(pos_order))
        journal_ids = set()
        for payments in pos_order['statement_ids']:
            if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
                order.add_payment(self._payment_fields(payments[2]))
            journal_ids.add(payments[2]['journal_id'])

        if pos_session.sequence_number <= pos_order['sequence_number']:
            pos_session.write({'sequence_number': pos_order['sequence_number'] + 1})
            pos_session.refresh()

        if not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_journal_id = pos_session.cash_journal_id.id
            if not cash_journal_id:
                # Select for change one of the cash journals used in this
                # payment
                cash_journal = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('id', 'in', list(journal_ids)),
                ], limit=1)
                if not cash_journal:
                    # If none, select for change one of the cash journals of the POS
                    # This is used for example when a customer pays by credit card
                    # an amount higher than total amount of the order and gets cash back
                    cash_journal = [statement.journal_id for statement in pos_session.statement_ids if statement.journal_id.type == 'cash']
                    if not cash_journal:
                        raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                cash_journal_id = cash_journal[0].id
            order.add_payment({
                'amount': -pos_order['amount_return'],
                'payment_date': fields.Datetime.now(),
                'payment_name': _('return'),
                'journal': cash_journal_id,
            })
        if pos_order['partner_id']:
            self.send_invoice(order)
            print(order.date_order)
            print(order.partner_id.name)
            for line in order.lines:
                print(line.product_id.name)
                print(line.qty)
                print(line.price_subtotal)

        return order


class Sakinah_Payment(models.Model):
    _inherit = "account.payment"

    state = fields.Selection([('draft', 'Draft'), ('saved', 'Saved'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled')], readonly=True, copy=False, string="Status")
    hide_validate = fields.Boolean('Hide Validate', compute='_compute_validation')
    pos_session = fields.Many2one('pos.session', string='POS Session')

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        # Set payment method domain
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}
        res['domain']['journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        res['domain']['destination_journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['destination_journal_id'].append(('type', 'in', ('bank', 'cash')))
        
        if self.payment_type == 'transfer':
            res['domain']['journal_id'].append(('users.id', '=', self.env.uid))
            res['domain']['destination_journal_id'].append(('journal_user', '=', False))
        else:
            res['domain']['journal_id'].append(('name', 'in', ('Bank', 'Cash')))

        return res

    @api.multi
    def save(self):
        context = self._context
        print(context)

        session_id = context.get('pos_session')
        if session_id:
            pos_session = self.env['pos.session'].search([('id', '=', session_id)])
            self.write({'pos_session': session_id})

        desjourname = self.destination_journal_id.name
        journame = self.journal_id.name
        writename = journame + " to " + desjourname
        self.write({'state': 'saved', 'name': writename})

    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        self.write({'state': 'draft'})

        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)
            if self.pos_session:
                st_line = self.env['account.bank.statement.line'].create({'name': move.name,'amount': -amount,'statement_id': rec.pos_session.statement_ids.id})
                move.write({'statement_line_id': st_line.id})

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

                print(transfer_debit_aml.debit)
                
                bal_start = 0
                last_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', '=', rec.destination_journal_id.id)], limit=1)
                if last_bnk_stmt:
                    bal_start = last_bnk_stmt.balance_end
                print(bal_start)
                bank_statement = self.env['account.bank.statement'].create({'name': 'Bank Statement', 'journal_id': rec.destination_journal_id.id, 'balance_start': bal_start})
                st_line2 = self.env['account.bank.statement.line'].create({'name': 'Bank Statement','amount': amount,'statement_id': bank_statement.id})
                bank_statement.write({'balance_end_real': bal_start + amount})
                st_line2.write({'journal_entry_ids': [(4, transfer_debit_aml.move_id.id)]})
                
                bank_statement.sudo().button_confirm_bank()

            rec.write({'state': 'posted', 'move_name': move.name})

    @api.depends('destination_journal_id')
    def _compute_validation(self):
        for pay in self:
            presence = 0
            for dest in pay.destination_journal_id.users:
                if dest.id == self.env.uid:
                    presence += 1
        
            if presence != 0:
                pay.hide_validate = False
            else:
                pay.hide_validate = True

class Sakinah_Expense(models.Model):
    _inherit = "hr.expense"

    @api.multi
    def _new_mode(self):
        return [("company_account", "Company")]

    payment_mode = fields.Selection(_new_mode, default='company_account', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, string="Payment By")

class Sakinah_Expense_Sheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.multi
    def _new_mode(self):
        return [("company_account", "Company")]

    payment_mode = fields.Selection(_new_mode, related='expense_line_ids.payment_mode', default='company_account', readonly=True, string="Payment By")
    hide_resubmit = fields.Boolean('Hide Resubmit', compute='_compute_resubmit')

    @api.depends('employee_id')
    def _compute_resubmit(self):
        for sh in self:
            presence = 0
            for em in sh.employee_id.user_id:
                if em.id == self.env.uid:
                    presence += 1
        
            if presence != 0:
                sh.hide_resubmit = False
            else:
                sh.hide_resubmit = True

class SPosBox(CashBox):
    _register = False

class SPosBoxOut(SPosBox):
    _inherit = 'cash.box.out'

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        if not record.journal_id.company_id.transfer_account_id:
            raise UserError(_("You should have defined an 'Internal Transfer Account' in your cash register's journal!"))
        amount = self.amount or 0.0
        return {
            'date': record.date,
            'statement_id': record.id,
            'journal_id': record.journal_id.id,
            'amount': -amount if amount > 0.0 else amount,
            'account_id': 19,
            'name': self.name,
        }

 

