# -*- coding: utf-8 -*-

import logging
from odoo import fields, models, api, exceptions, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger('__name__')


class RetentionVat(models.Model):
    """This is a main model for rentetion vat control."""
    _inherit = 'isrl.retention'

    def action_post(self):
        super().action_post()
        self.concilio_saldo_pendiente_isrl()


    def concilio_saldo_pendiente_isrl(self):
        id_islr=self.id
        tipo_empresa=self.type
        if tipo_empresa=="in_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="in_receipt":#aqui si la empresa es un proveedor
            type_internal="payable"
        if tipo_empresa=="out_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="out_receipt":# aqui si la empresa es cliente
            type_internal="receivable"
        busca_movimientos = self.env['account.move'].search([('isrl_ret_id','=',id_islr)])
        #raise UserError(_('busca_movimientos = %s')%busca_movimientos)
        for det_movimientos in busca_movimientos:
            busca_line_mov = self.env['account.move.line'].search([('move_id','=',det_movimientos.id)])
            for b_l_m in busca_line_mov:
                if b_l_m.account_id.user_type_id.type==type_internal:
                    if b_l_m.credit==0:
                        id_move_debit=b_l_m.id
                        monto_debit=b_l_m.debit
                    if b_l_m.debit==0:
                        id_move_credit=b_l_m.id
                        monto_credit=b_l_m.credit
        if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="in_receipt":
            monto=monto_debit
        if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="out_receipt":
            monto=monto_credit
        value = {
             'debit_move_id':id_move_debit,
             'credit_move_id':id_move_credit,
             'amount':monto,
             'debit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('out_invoice','out_receipt') else monto,
             'credit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('in_invoice','in_receipt') else monto,
             'max_date':self.date_move,
        }
        self.env['account.partial.reconcile'].create(value)

    def conv_div_extranjera(self,valor):
        self.invoice_id.currency_id.id
        fecha_contable_doc=self.invoice_id.date
        monto_factura=self.invoice_id.amount_total
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if self.invoice_id.currency_id.id!=self.invoice_id.company_id.currency_id.id:
            tasa= self.env['res.currency.rate'].search([('currency_id','=',self.invoice_id.currency_id.id),('name','<=',self.invoice_id.date)],order="name asc")
            for det_tasa in tasa:
                if fecha_contable_doc>=det_tasa.name:
                    valor_aux=det_tasa.rate
            rate=round(1/valor_aux,2)  # LANTA
            #rate=round(valor_aux,2)  # ODOO SH
            resultado=valor/rate
        else:
            resultado=valor
        return resultado






class AccountMove(models.Model):
    _inherit = 'vat.retention'

    def action_posted(self):
        super().action_posted()
        self.concilio_saldo_pendiente()

    def concilio_saldo_pendiente(self):
        id_retention=self.id
        tipo_empresa=self.move_id.type
        if tipo_empresa=="in_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="in_receipt":#aqui si la empresa es un proveedor
            type_internal="payable"
        if tipo_empresa=="out_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="out_receipt":# aqui si la empresa es cliente
            type_internal="receivable"
        busca_movimientos = self.env['account.move'].search([('vat_ret_id','=',id_retention)])
        for det_movimientos in busca_movimientos:
            busca_line_mov = self.env['account.move.line'].search([('move_id','=',det_movimientos.id)])
            for b_l_m in busca_line_mov:
                if b_l_m.account_id.user_type_id.type==type_internal:
                    if b_l_m.credit==0:
                        id_move_debit=b_l_m.id
                        monto_debit=b_l_m.debit
                    if b_l_m.debit==0:
                        id_move_credit=b_l_m.id
                        monto_credit=b_l_m.credit
        if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="in_receipt":
            monto=monto_debit
        if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="out_receipt":
            monto=monto_credit
        value = {
             'debit_move_id':id_move_debit,
             'credit_move_id':id_move_credit,
             'amount':monto,
             'debit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('out_invoice','out_receipt') else monto,
             'credit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('in_invoice','in_receipt') else monto,
             'max_date':self.accouting_date,
        }
        self.env['account.partial.reconcile'].create(value)

    def conv_div_extranjera(self,valor):
        self.invoice_id.currency_id.id
        fecha_contable_doc=self.invoice_id.date
        monto_factura=self.invoice_id.amount_total
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if self.invoice_id.currency_id.id!=self.company_id.currency_id.id:
            tasa= self.env['res.currency.rate'].search([('currency_id','=',self.invoice_id.currency_id.id),('name','<=',self.invoice_id.date)],order="name asc")
            for det_tasa in tasa:
                if fecha_contable_doc>=det_tasa.name:
                    valor_aux=det_tasa.rate
            rate=round(1/valor_aux,2)  # LANTA
            #rate=round(valor_aux,2)  # ODOO SH
            resultado=valor/rate
        else:
            resultado=valor
        return resultado

class MUnicipalityTax(models.Model):
    _inherit = 'municipality.tax'

    def action_post(self):
        super().action_post()
        self.concilio_saldo_pendiente_muni()



    def concilio_saldo_pendiente_muni(self):
        id_municipality=self.id
        tipo_empresa=self.invoice_id.type
        if tipo_empresa=="in_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="in_receipt":#aqui si la empresa es un proveedor
            type_internal="payable"
        if tipo_empresa=="out_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="out_receipt":# aqui si la empresa es cliente
            type_internal="receivable"
        busca_movimientos = self.env['account.move'].search([('wh_muni_id','=',id_municipality)])
        #raise UserError(_('busca_movimientos = %s')%busca_movimientos)
        for det_movimientos in busca_movimientos:
            busca_line_mov = self.env['account.move.line'].search([('move_id','=',det_movimientos.id)])
            for b_l_m in busca_line_mov:
                if b_l_m.account_id.user_type_id.type==type_internal:
                    if b_l_m.credit==0:
                        id_move_debit=b_l_m.id
                        monto_debit=b_l_m.debit
                    if b_l_m.debit==0:
                        id_move_credit=b_l_m.id
                        monto_credit=b_l_m.credit
        if tipo_empresa=="in_invoice" or tipo_empresa=="out_refund" or tipo_empresa=="in_receipt":
            monto=monto_debit
        if tipo_empresa=="out_invoice" or tipo_empresa=="in_refund" or tipo_empresa=="out_receipt":
            monto=monto_credit
        value = {
             'debit_move_id':id_move_debit,
             'credit_move_id':id_move_credit,
             'amount':monto,
             'debit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('out_invoice','out_receipt') else monto,
             'credit_amount_currency':self.conv_div_extranjera(monto) if tipo_empresa in ('in_invoice','in_receipt') else monto,
             'max_date':self.transaction_date,
        }
        self.env['account.partial.reconcile'].create(value)

    def conv_div_extranjera(self,valor):
        self.invoice_id.currency_id.id
        fecha_contable_doc=self.invoice_id.date
        monto_factura=self.invoice_id.amount_total
        valor_aux=0
        #raise UserError(_('moneda compañia: %s')%self.company_id.currency_id.id)
        if self.invoice_id.currency_id.id!=self.company_id.currency_id.id:
            tasa= self.env['res.currency.rate'].search([('currency_id','=',self.invoice_id.currency_id.id),('name','<=',self.invoice_id.date)],order="name asc")
            for det_tasa in tasa:
                if fecha_contable_doc>=det_tasa.name:
                    valor_aux=det_tasa.rate
            rate=round(1/valor_aux,2)  # LANTA
            #rate=round(valor_aux,2)  # ODOO SH
            resultado=valor/rate
        else:
            resultado=valor
        return resultado