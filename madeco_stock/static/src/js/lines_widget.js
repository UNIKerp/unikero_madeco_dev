odoo.define('madeco_stock.LinesWidget', function (require) {
    'use strict';

    const LinesWidget = require('stock_barcode.LinesWidget');

    LinesWidget.include({
        init: function (parent, page, pageIndex, nbPages) {
            this._super.apply(this, arguments);
            this.isPackagingHidden = parent.currentState.is_packaging_hidden;
        }
    });

});
