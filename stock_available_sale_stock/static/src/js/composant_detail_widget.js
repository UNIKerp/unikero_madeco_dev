odoo.define('stock_available_sale_stock.ComponentDetailWidget', function (require) {
    "use strict";
    
    var core = require('web.core');
    var QWeb = core.qweb;
    
    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    var utils = require('web.utils');
    
    var _t = core._t;
    var time = require('web.time');
    
    var ComponentDetailWidget = Widget.extend({
        template: 'stock_available_sale_stock.ComponantDetail',
        events: _.extend({}, Widget.prototype.events, {
            'click .fa-circle': '_onClickButton',
        }),
    
        /**
         * @override
         * @param {Widget|null} parent
         * @param {Object} params
         */
        init: function (parent, params) {
            this.data = params.data;
            this.fields = params.fields;
            this._super(parent);
            console.log(this);
        },
    
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._setPopOver();
            });
        },
    
        /**
         * Redirect to the product graph view.
         *
         * @private
         * @param {MouseEvent} event
         * @returns {Promise} action loaded
         */
        async _openForecast(ev) {
            ev.stopPropagation();
            // TODO: in case of kit product, the forecast view should show the kit's components (get_component)
            // The forecast_report doesn't not allow for now multiple products 
            var action = await this._rpc({
                model: 'product.product',
                method: 'action_product_forecast_report',
                args: [[this.data.product_id.data.id]]
            });
            action.context = {
                active_model: 'product.product',
                active_id: this.data.product_id.data.id,
                warehouse: this.data.warehouse_id && this.data.warehouse_id.res_id
            };
            return this.do_action(action);
        },
        _getContent() {
            const $content = $(QWeb.render('stock_available_sale_stock.ComponentDetailPopOver', {
                data: this.data,
            }));
            $content.on('click', '.action_open_forecast', this._openForecast.bind(this));
            return $content;
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Set a bootstrap popover on the current ComponentDetail widget 
         */
        _setPopOver() {
            const $content = this._getContent();
            if (!$content) {
                return;
            }
            const options = {
                content: $content,
                html: true,
                placement: 'left',
                title: _t('Component detail'),
                trigger: 'focus',
                delay: {'show': 0, 'hide': 100 },
            };
            this.$el.popover(options);
        },
    
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onClickButton: function () {
            // We add the property special click on the widget link.
            // This hack allows us to trigger the popover (see _setPopOver) without
            // triggering the _onRowClicked that opens the order line form view.
            this.$el.find('.fa-circle').prop('special_click', true);
        },
    });
    
    widget_registry.add('component_detail_widget', ComponentDetailWidget);
    
    return ComponentDetailWidget;
    });
    