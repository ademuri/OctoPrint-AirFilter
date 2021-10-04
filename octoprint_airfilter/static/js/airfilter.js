/*
 * View model for OctoPrint-AirFilter
 *
 * Author: Adam DeMuri
 * License: Apache2
 */
$(function() {
    function AirfilterViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        self.is_on = ko.observable(false);
        self.sgp_raw = ko.observable(0);
        self.sgp_index = ko.observable(0);

        self.prettyState = ko.pureComputed(() => {
            return self.is_on() ? 'On' : 'Off';
        });

        self.updateState = () => {
            return $.getJSON("/plugin/airfilter/state", (data) => {
                console.log(data);
                self.is_on(data['state']);
                if (data['sgp_raw'] > 0) {
                    self.sgp_raw(data['sgp_raw']);
                }
                if (data['sgp_index'] > 0) {
                    self.sgp_index(data['sgp_index']);
                }
            });
        }

        self.onAfterBinding = () => {
            self.updateState();
            setInterval(self.updateState, 60 * 1000);
        }

        self.toggle = () => {
            const request = {"command": "toggle"};
            $.ajax({
                url: "/plugin/airfilter/toggle",
                type: "POST",
                data: ko.toJSON(request),
                contentType:"application/json; charset=utf-8",
                dataType:"json",
                success: function(){
                    self.updateState();
                }
              });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: AirfilterViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_airfilter, #tab_plugin_airfilter, ...
        elements: ["#air-filter-status", "#tab_plugin_airfilter"],
    });
});
