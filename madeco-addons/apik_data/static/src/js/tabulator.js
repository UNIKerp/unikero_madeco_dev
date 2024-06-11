odoo.define('apik_data.tabulator', function (require) {
    var core = require('web.core');
    var qweb = core.qweb;

	var fieldRegistry = require('web.field_registry');
    var BasicField = require('web.basic_fields');
    
    var FieldText = BasicField.FieldText;

    
	var field_tabulator = FieldText.extend({
	    tag_template: "FieldTabulator",
	    
        init: function () {
            this._super.apply(this, arguments);
            this.parent = this.getParent();
            this.resetOnAnyFieldChange = false;
        },
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
                      
        

        },
        _render: function(){
            this._super.apply(this, arguments);
            var self = this;
            if (self.mode != "edit"){
                this.$el.html(qweb.render(this.tag_template));
                try {
                    var result = JSON.parse(self.value);
                    var content = self.$el.find('.tabulator')[0];
                    var table = new Tabulator(content,{
                        reactiveData:true,
                        columns : result['column'],
                        layout: "fitColumns",
                        pagination: "local",
                        paginationSize: 100,
                    }); 
                    table.setData(result['data']);
                    table.redraw(true);
                    
                    self.$el.find("#download-xlsx").click(function(){
                        console.log("download");
                        table.download("xlsx", "data.xlsx", {sheetName:"Apik Data"});
                    });
                    self.$el.find("#download-csv").click(function(){
                        table.download("csv", "data.csv", { delimiter: "|" });
                    });
                    
                } catch(error){
                    console.error(error);
                }
            }
        }
        
	});
	
	
	fieldRegistry.add('tabulator', field_tabulator);
	
	return {
		field_tabulator: field_tabulator,
	}
	
	
});
