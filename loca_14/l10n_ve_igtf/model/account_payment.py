# coding: utf-8
###########################################################################

import logging

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

#_logger = logging.getLogger(__name__)
class account_payment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'
    #name =fields.Char(compute='_valor_anticipo')
    darrell = fields.Char()

    #Este campo es para el modulo IGTF
    move_itf_id = fields.Many2one('account.move', 'Asiento contable')

    #Estos Campos son para el modulo de anticipo
    tipo = fields.Char()
    anticipo = fields.Boolean(defaul=False)
    usado = fields.Boolean(defaul=False)
    anticipo_move_id = fields.Many2one('account.move', 'Id de Movimiento de anticipo donde pertenece dicho pago')
    saldo_disponible = fields.Monetary(string='Saldo Disponible')
    move_id = fields.Many2one('account.move')
    factura_id = fields.Many2one('account.move', 'Id de Movimiento o factura donde pertenece dicho pago')

    def _valor_anticipo(self):
        nombre=self.name
        saldo=self.saldo_disponible
        self.name=nombre

    def action_post(self):
        super().action_post()
        #raise UserError(_('cuenta id = %s')%self.id)
        pago_id=self.id
        self.button_organizar_igtf(pago_id)
        self.direccionar_cuenta_anticipo(pago_id)


    
    def direccionar_cuenta_anticipo(self,id_pago):
        cuenta_anti_cliente = self.partner_id.account_anti_receivable_id.id
        cuenta_anti_proveedor = self.partner_id.account_anti_payable_id.id
        cuenta_cobrar = self.partner_id.property_account_receivable_id.id
        cuenta_pagar = self.partner_id.property_account_payable_id.id
        anticipo = self.anticipo
        tipo_persona = self.partner_type
        tipo_pago = self.payment_type
        #raise UserError(_('tipo = %s')%tipo_pago)
        if anticipo==True:
            if tipo_persona=="supplier":
                tipoo='in_invoice'
            if tipo_persona=="customer":
                tipoo='out_invoice'
            self.tipo=tipoo
            if not cuenta_anti_proveedor:
                raise UserError(_('Esta Empresa no tiene asociado una cuenta de anticipo para proveedores/clientes. Vaya al modelo res.partner, pestaña contabilidad y configure'))
            if not cuenta_anti_cliente:
                raise UserError(_('Esta Empresa no tiene asociado una cuenta de anticipo para proveedores/clientes. Vaya al modelo res.partner, pestaña contabilidad y configure'))
            if cuenta_anti_cliente and cuenta_anti_proveedor:
                if tipo_persona=="supplier":
                    cursor_move_line = self.env['account.move.line'].search([('payment_id','=',self.id),('account_id','=',cuenta_pagar)])
                    for det_cursor in cursor_move_line:
                        self.env['account.move.line'].browse(det_cursor.id).write({
                            'account_id':cuenta_anti_proveedor,
                            })
                    #raise UserError(_('cuenta id = %s')%cursor_move_line.account_id.id)
                if tipo_persona=="customer":
                    cursor_move_line = self.env['account.move.line'].search([('payment_id','=',self.id),('account_id','=',cuenta_cobrar)])
                    for det_cursor in cursor_move_line:
                        self.env['account.move.line'].browse(det_cursor.id).write({
                            'account_id':cuenta_anti_cliente,
                            })
                    #raise UserError(_('cuenta id = %s')%cursor_move_line.account_id.id)
                self.saldo_disponible=self.amount
        else:
            return 0


    def button_organizar_igtf(self,id_pago):

        #raise UserError(_('El Ide es= %s')%id_pago)
        #raise UserError(_('nombre = %s')%self.display_name+"[ Bs. "+str(33)+"]")
        company_id=self._get_company().id
        lista_company=self.env['res.company'].search([('id','=',company_id)])
        for det_company in lista_company:
            porcentage_igtf=det_company.wh_porcentage
            cuenta_igtf=det_company.account_wh_itf_id
            habilita_igtf=det_company.calculate_wh_itf

        if habilita_igtf==True:
            tipo_bank=self.journal_id.tipo_bank
            typo=self.journal_id.type
            if typo=="bank":
                if tipo_bank==False:
                   raise UserError(_('El banco de este diario no tiene definido la nacionalidad'))
                else:
                    if tipo_bank=="na":
                        lista_pago= self.env['account.payment'].search([('id','=',id_pago)])
                        for det_pago in lista_pago:
                            id_pago=det_pago.id
                            move_name=det_pago.move_id.name
                            tipo_pago=det_pago.payment_type
                            tipo_persona=det_pago.partner_type
                            monto_total=det_pago.amount
                            #raise UserError(_('El monto_total = %s')%monto_total)
                            if tipo_pago=='outbound':
                                if tipo_persona=='supplier':
                                    """lista_move= self.env['account.move'].search([('name','=',move_name)])
                                    for det_move in lista_move:
                                        monto_total=det_move.amount_total
                                        state=det_move.state
                                        date=det_move.date"""


                                    nombre_igtf = self.get_name()
                                    id_move=self.registro_movimiento_pago_igtf(porcentage_igtf,monto_total,nombre_igtf)
                                    idv_move=id_move.id # Aqui obtengo el id del registro de la tabla account_move y lo guarda en estado draft
                                    valor=self.registro_movimiento_linea_pago_igtf(porcentage_igtf,idv_move,monto_total,nombre_igtf,id_pago)
                                    """ Codigo de odoo que tome para que validara el asiento contable """
                                    moves= self.env['account.move'].search([('id','=',idv_move)])
                                    moves._post(soft=False)#filtered(lambda move: move.journal_id.post_at != 'bank_rec').post() #esto es de odoo 13
                                    """ Fin codigo de odoo que valida asiento contable """
                                    #raise UserError(_('El id move es = %s')%moves)
                                    self.env['account.payment'].browse(id_pago).write({'move_itf_id': id_move.id,'move_name':move_name})


    def registro_movimiento_pago_igtf(self,igtf_porcentage,total_monto,igtf_nombre):
        name = igtf_nombre
        amount_itf = round(float(total_monto) * float((igtf_porcentage / 100.00)),2)
        #raise UserError(_('monto xx = %s')%amount_itf)
        value = {
            #'name': igtf_nombre,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'line_ids': False,
            'state': 'draft',
            'move_type': "entry",# estte campo es el que te deja cambiar y almacenar valores 
            'type':"entry",
            'amount_total':total_monto,# revisar
            'amount_total_signed':total_monto,# revisar
            'partner_id': self.partner_id.id,
            'ref': "Nro %s Comisión del %s %% del pago %s" % (igtf_nombre,igtf_porcentage,self.move_id.name),

        }
        move_obj = self.env['account.move']
        move_id = move_obj.create(value)     
        return move_id

    def registro_movimiento_linea_pago_igtf(self,igtf_porcentage,id_movv,total_monto,igtf_nombre,idd_pago):
        #raise UserError(_('ID MOVE = %s')%id_movv)
        amount_itf = round(float(total_monto) * float((igtf_porcentage / 100.00)),2)
        valores=amount_itf
        #name = igtf_nombre        
        #raise UserError(_('valores = %s')%valores)
        value = {
             'name': igtf_nombre,
             'ref' : "Nro %s Comisión del %s %% del pago %s" % (igtf_nombre,igtf_porcentage,self.move_id.name),
             'move_id': int(id_movv),
             'date': self.payment_date,
             'partner_id': self.partner_id.id,
             'journal_id': self.journal_id.id,
             'account_id': self.journal_id.default_debit_account_id.id,
             'amount_currency': 0.0,
             'date_maturity': False,
             #'credit': float(amount_itf),
             #'debit': 0.0,
             'credit': valores,
             'debit': 0.0, # aqi va cero
             'balance':-valores,
             'payment_id':idd_pago,

        }
        move_line_obj = self.env['account.move.line']
        move_line_id1 = move_line_obj.create(value)

        value['account_id'] = self._get_company().account_wh_itf_id.id
        value['credit'] = 0.0 # aqui va cero
        value['debit'] = valores
        value['balance'] = valores


        move_line_id2 = move_line_obj.create(value)

        

    @api.model
    def check_partner(self):
        '''metodo que chequea el rif de la empresa y la compañia si son diferentes
        retorna True y si son iguales retorna False'''
        idem = False
        company_id = self._get_company()
        for pago in self:
            if pago.partner_id.vat != company_id.partner_id.vat:
                idem = True
                return idem
        return idem

    def _get_company_itf(self):
        '''Método que retorna verdadero si la compañia debe retener el impuesto ITF'''
        company_id = self._get_company()
        if company_id.calculate_wh_itf:
            return True
        return False

    @api.model
    def _get_company(self):
        '''Método que busca el id de la compañia'''
        company_id = self.env['res.users'].browse(self.env.uid).company_id
        return company_id

    @api.model
    def check_payment_type(self):
        '''metodo que chequea que el tipo de pago si pertenece al tipo outbound'''
        type_bool = False
        for pago in self:
            type_payment = pago.payment_type
            if type_payment == 'outbound':
                type_bool = True
        return type_bool

    def get_name(self):
        '''metodo que crea el Nombre del asiento contable si la secuencia no esta creada, crea una con el
        nombre: 'l10n_account_withholding_itf'''

        self.ensure_one()
        SEQUENCE_CODE = 'l10n_ve_cuenta_retencion_itf'
        company_id = self._get_company()
        IrSequence = self.env['ir.sequence'].with_context(force_company=company_id.id)
        name = IrSequence.next_by_code(SEQUENCE_CODE)

        # si aún no existe una secuencia para esta empresa, cree una
        if not name:
            IrSequence.sudo().create({
                'prefix': 'IGTF',
                'name': 'Localización Venezolana impuesto ITF %s' % company_id.id,
                'code': SEQUENCE_CODE,
                'implementation': 'no_gap',
                'padding': 8,
                'number_increment': 1,
                'company_id': company_id.id,
            })
            name = IrSequence.next_by_code(SEQUENCE_CODE)
        return name

    def action_draft(self):
        id_pago=self.id
        move_itf_idd=self.move_itf_id.id
        if move_itf_idd:
            mov_igtf=self.env['account.move'].search([('id','=',move_itf_idd)])
            mov_igtf.filtered(lambda move: move.state == 'posted').button_draft()
            mov_igtf.with_context(force_delete=True).unlink()

        # CODIGO ORIGINAL DEL SISTEMA NO TOCAR
        self.move_id.button_draft()
        ##moves = self.mapped('move_line_ids.move_id')
        ##moves.filtered(lambda move: move.state == 'posted').button_draft()
        ##moves.with_context(force_delete=True).unlink()
        ##self.write({'state': 'draft'})
        # FIN CODIGO ORIGINAL