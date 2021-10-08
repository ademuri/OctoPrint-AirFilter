/*
 * View model for OctoPrint-AirFilter
 *
 * Author: Adam DeMuri
 * License: Apache2
 */
$(function() {
    function AirfilterViewModel(parameters) {
        let self = this;
        const colors = ["#F88", "#FB8", "#FF8", "#BF8", "#8F8"];

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        self.is_on = ko.observable(false);
        self.sgp_raw = ko.observable(0);
        self.sgp_index = ko.observable(0);
        self.history = ko.observableArray();
        self.indexMin = 0;
        self.indexMax = 0;
        self.rawMin = 0;
        self.rawMax = 0;

        self.prettyState = ko.pureComputed(() => {
            return self.is_on() ? 'On' : 'Off';
        });

        self.updateState = () => {
            return $.getJSON("/plugin/airfilter/state", (data) => {
                self.is_on(data['state']);
                if (data['sgp_raw'] > 0) {
                    self.sgp_raw(data['sgp_raw']);
                }
                if (data['sgp_index'] > 0) {
                    self.sgp_index(data['sgp_index']);
                }
            });
        }

        self.getHistory = () => {
            $.getJSON("/plugin/airfilter/history", (data) => {
                self.indexMin = data.history.map(a => a.index).reduce((a, b) => Math.min(a, b));
                self.indexMax = data.history.map(a => a.index).reduce((a, b) => Math.max(a, b));
                self.rawMin = data.history.map(a => a.raw).reduce((a, b) => Math.min(a, b));
                self.rawMax = data.history.map(a => a.raw).reduce((a, b) => Math.max(a, b));
                self.history(data.history);
            });
        };

        self.onAfterBinding = () => {
            setTimeout(self.updateState, 0);
            setInterval(self.updateState, 60 * 1000);
            setTimeout(self.getHistory, 0);
            setInterval(self.getHistory, 5 * 60 * 1000);
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

        self.indexColor = (index) => {
            return colors.reverse()[Math.round((index - self.indexMin) / (self.indexMax - self.indexMin) * (colors.length - 1))];
        };

        self.rawColor = (raw) => {
            return colors[Math.round((raw - self.rawMin) / (self.rawMax - self.rawMin) * (colors.length - 1))];
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
