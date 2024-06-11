odoo.define("apik_pdp.ClientAction", function (require) {
  "use strict";

  var ClientAction = require("mrp_mps.ClientAction");
  var core = require("web.core");
  var Dialog = require("web.Dialog");
  var QWeb = core.qweb;
  var _t = core._t;

  var MyClientAction = ClientAction.include({
    events: _.extend({}, ClientAction.prototype.events, {
      "click .o_mrp_mps_delete": "_onDeleteProducts",
      "click .o_mrp_mps_import": "_onImport",
      "click .o_mrp_mps_export": "_onExport",
    }),
    _onImport: function (ev) {
      ev.preventDefault();
      var self = this;

      var exitCallback = function () {};

      this.mutex.exec(function () {
        return self.do_action("apik_pdp.launch_pdp_import_wizard", {
          on_close: exitCallback,
        });
      });
    },
    _onExport: function (ev) {
      ev.preventDefault();
      var self = this;

      var exitCallback = function () {};

      this.mutex.exec(function () {
        return self.do_action("apik_pdp.launch_pdp_export_wizard", {
          on_close: exitCallback,
        });
      });
    },

    _onDeleteProducts: function (ev) {
      ev.preventDefault();
      var ids = [];
      var self = this;
      function doIt() {
        self.mutex.exec(function () {
          return self
            ._rpc({
              model: "mrp.production.schedule",
              method: "unlink",
              args: [ids],
            })
            .then(function () {
              self._reloadContent();
            });
        });
      }
      console.log($(".o_mps_content"));
      var elements = $(".o_mps_content");
      elements.each(function (el) {
        console.log($(elements[el]).data("id"));
        ids.push($(elements[el]).data("id"));
      });

      Dialog.confirm(
        this,
        _t("Are you sure you want to delete all products ?"),
        {
          confirm_callback: doIt,
        }
      );
    },
    _createProduct: function () {
      var self = this;
      var exitCallback = function () {
        return self
          ._rpc({
            model: "mrp.production.schedule",
            method: "search_read",
            args: [[], ["id"]],
            //limit: 1,
            orderBy: [{ name: "id", asc: false }],
          })
          .then(function (result) {
            if (result.length) {
              var res = [];
              result.forEach(function (el) {
                res.push(el.id);
              });
              self
                ._rpc({
                  model: "mrp.production.schedule",
                  method: "get_production_schedule_view_state",
                  args: [res],
                })
                .then(function (states) {
                  for (var i = 0; i < states.length; i++) {
                    var state = states[i];
                    var index = _.findIndex(self.state, { id: state.id });
                    if (index >= 0) {
                      self.state[index] = state;
                    } else {
                      self.state.push(state);
                    }
                  }
                  return self._renderState(states);
                });
            }
          });
      };
      this.mutex.exec(function () {
        return self.do_action("apik_pdp.action_mrp_mps_multi_form_view", {
          on_close: exitCallback,
        });
      });
    },
  });
});
