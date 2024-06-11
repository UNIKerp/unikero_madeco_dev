odoo.define('stock_multi_packaging.picking_client_action', function (require) {
    'use strict';

    var core = require('web.core');
    var PickingClientAction = require('stock_barcode.picking_client_action');
    // var ClientAction = require('stock_barcode.ClientAction');
    // var ViewsWidget = require('stock_barcode.ViewsWidget');
    var _t = core._t;



    PickingClientAction.include({
        /**
         *
         * @override
         */
        _validate: function (context) {
            const self = this;

            this.mutex.exec(function () {
                const successCallback = function () {
                    self.displayNotification({
                        message: _t("The transfer has been validated"),
                        type: 'success',
                    });
                    self.trigger_up('exit');
                };
                const exitCallback = function (infos) {
                    console.log(infos)
                    // if ((infos === undefined || !infos.special) && this.dialog.$modal.is(':visible')) {
                    //     successCallback();
                    // }
                    successCallback();
                    core.bus.on('barcode_scanned', self, self._onBarcodeScannedHandler);
                };

                return self._save().then(() => {
                    return self._rpc({
                        model: self.actionParams.model,
                        method: self.methods.validate,
                        context: context || {},
                        args: [[self.currentState.id]],
                    }).then((res) => {
                        console.log('superValidate')
                        console.log(res)

                        if (_.isObject(res)) {
                            core.bus.off('barcode_scanned', self, self._onBarcodeScannedHandler);
                            // if (res.type && res.type === 'ir.actions.report') {
                            //     var options = {
                            //         on_close: exitCallback,
                            //     };
                            // }
                            var options = {
                                on_close: exitCallback,
                            };

                            console.log(options)
                            return self.do_action(res, options);
                        } else {
                            return successCallback();
                        }
                    });
                });
            });
        },        

    });
});
