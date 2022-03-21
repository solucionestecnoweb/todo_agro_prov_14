

odoo.define('mt_pos_payment.screens', function (require) {
    'use strict';

    const { Printer } = require('point_of_sale.Printer');
    const { is_email } = require('web.utils');
    const { useRef, useContext } = owl.hooks;
    const { useErrorHandlers, onChangeOrder } = require('point_of_sale.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');

    const ReceiptScreen = (AbstractReceiptScreen) => {
        class ReceiptScreen extends AbstractReceiptScreen {
            constructor() {
                super(...arguments);
                useErrorHandlers();
                onChangeOrder(null, (newOrder) => newOrder && this.render());
                this.orderReceipt = useRef('order-receipt');
                const order = this.currentOrder;
                const client = order.get_client();
                this.orderUiState = useContext(order.uiState.ReceiptScreen);
                this.orderUiState.inputEmail = this.orderUiState.inputEmail || (client && client.email) || '';
                this.is_email = is_email;
            }
            mounted() {
                // Here, we send a task to the event loop that handles
                // the printing of the receipt when the component is mounted.
                // We are doing this because we want the receipt screen to be
                // displayed regardless of what happen to the handleAutoPrint
                // call.
                setTimeout(async () => await this.handleAutoPrint(), 0);
            }
            async onSendEmail() {
                console.log(this.orderUiState)
                const order = this.currentOrder;
                const client = order.get_client();
                const orderName = order.get_name();
                const orderClient = { email: this.orderUiState.inputEmail, name: client ? client.name : this.orderUiState.inputEmail };
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                const tipLine = order.get_orderlines()

                console.log(order)
                console.log(client)
                console.log(orderClient)
                console.log(order_server_id)
                console.log(tipLine)

                if (!is_email(this.orderUiState.inputEmail)) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = this.env._t('Invalid email.');
                    return;
                }
                try {
                    await this._sendReceiptToCustomer();
                    this.orderUiState.emailSuccessful = true;
                    this.orderUiState.emailNotice = this.env._t('Email sent.');
                } catch (error) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = this.env._t('Sending email failed. Please try again.');
                }
            }
            async ImprimirFPV() {
                const order = this.currentOrder;
                const orderName = order.get_name();
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                window.open(order.pos.company.website + "my/invoices/natural/" + order.name, "width=300,height=500,scrollbars=YES")

            }
            async ImprimirNota() {
                const order = this.currentOrder;
                const orderName = order.get_name();
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                window.open(order.pos.company.website + "my/invoices/nota/" + order.name, "width=300,height=500,scrollbars=YES")

            }
            async ImprimirFiscal () {
                const order = this.currentOrder;
                console.log(order)
                var lineas = [] 
                console.log(order.changed.client)
                for (var i = 0; i < order.orderlines.models.length; i += 1) {
                    var id_impuesto = order.orderlines.models[i].product.taxes_id
                    var valor_impuesto = "0"
                    for (var j = 0; j < order.pos.taxes.length; j += 1) {
                        if (id_impuesto == order.pos.taxes[j].id){

                            if (order.pos.taxes[j].amount == 0){
                                valor_impuesto = "0"
                            }
                            if (order.pos.taxes[j].amount == 16) {
                                valor_impuesto = "1"
                            }
                            if (order.pos.taxes[j].amount == 8) {
                                valor_impuesto = "2"
                            }
                            if (order.pos.taxes[j].amount == 31) {
                                valor_impuesto = "3"
                            } 
                        }
                    }
                    lineas.push({
                        'product': order.orderlines.models[i].product.default_code.replace('&', '') + " "+order.orderlines.models[i].product.display_name.replace('&', ''),
                        'cantidad': order.orderlines.models[i].quantity,
                        'precio':   order.orderlines.models[i].price,
                        'impuesto': valor_impuesto
                    })
                }
                
                var enviar_lineas = JSON.stringify(lineas);
                window.open("http://localhost/fiscal_13/cargar.php?cid=" + order.name + "&numero_recibo=" + order.name + "&cliente=" + order.changed.client.name.replace('&', '') + "&telefono=" + order.changed.client.phone + "&direccion=" + order.changed.client.address + "&rif_cedula=" + order.changed.client.vat + "&lineas=" + enviar_lineas + "&order_id=" + 666, "width=300,height=500,scrollbars=YES")
            }
            get orderAmountPlusTip() {
                const order = this.currentOrder;
                const orderTotalAmount = order.get_total_with_tax();
                const tip_product_id = this.env.pos.config.tip_product_id && this.env.pos.config.tip_product_id[0];
                const tipLine = order
                    .get_orderlines()
                    .find((line) => tip_product_id && line.product.id === tip_product_id);
                const tipAmount = tipLine ? tipLine.get_all_prices().priceWithTax : 0;
                const orderAmountStr = this.env.pos.format_currency(orderTotalAmount - tipAmount);
                if (!tipAmount) return orderAmountStr;
                const tipAmountStr = this.env.pos.format_currency(tipAmount);
                return `${orderAmountStr} + ${tipAmountStr} tip`;
            }
            get currentOrder() {
                return this.env.pos.get_order();
            }
            get nextScreen() {
                return { name: 'ProductScreen' };
            }
            whenClosing() {
                this.orderDone();
            }
            /**
             * This function is called outside the rendering call stack. This way,
             * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
             * any error that can happen during the printing does not affect the rendering.
             */
            async handleAutoPrint() {
                if (this._shouldAutoPrint()) {
                    await this.printReceipt();
                    if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                        this.whenClosing();
                    }
                }
            }
            orderDone() {
                this.currentOrder.finalize();
                const { name, props } = this.nextScreen;
                this.showScreen(name, props);
            }
            async printReceipt() {
                const isPrinted = await this._printReceipt();
                if (isPrinted) {
                    this.currentOrder._printed = true;
                }
            }
            _shouldAutoPrint() {
                return this.env.pos.config.iface_print_auto && !this.currentOrder._printed;
            }
            _shouldCloseImmediately() {
                var invoiced_finalized = this.currentOrder.is_to_invoice() ? this.currentOrder.finalized : true;
                return this.env.pos.proxy.printer && this.env.pos.config.iface_print_skip_screen && invoiced_finalized;
            }
            async _sendReceiptToCustomer() {
                const printer = new Printer(null, this.env.pos);
                const receiptString = this.orderReceipt.comp.el.outerHTML;
                const ticketImage = await printer.htmlToImg(receiptString);
                const order = this.currentOrder;
                const client = order.get_client();
                const orderName = order.get_name();
                const orderClient = { email: this.orderUiState.inputEmail, name: client ? client.name : this.orderUiState.inputEmail };
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                await this.rpc({
                    model: 'pos.order',
                    method: 'action_receipt_to_customer',
                    args: [[order_server_id], orderName, orderClient, ticketImage],
                });
            }
        }
        ReceiptScreen.template = 'ReceiptScreen';
        return ReceiptScreen;
    };

    Registries.Component.addByExtending(ReceiptScreen, AbstractReceiptScreen);

    return ReceiptScreen;
});

