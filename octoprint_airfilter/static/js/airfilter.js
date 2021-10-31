/*
 * View model for OctoPrint-AirFilter
 *
 * Author: Adam DeMuri
 * License: Apache2
 */
$(function() {
    function AirfilterViewModel(parameters) {
        let self = this;
        self.colors = ["#F88", "#DA8", "#BB8", "#AD8", "#8F8"];

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        self.is_on = ko.observable(false);
        self.filter_life = ko.observable(null);
        self.sgp_raw = ko.observable(null);
        self.sgp_index = ko.observable(null);
        self.temperature = ko.observable(null);
        self.relative_humidity = ko.observable(null);
        self.history = ko.observableArray();
        self.duty = ko.observable(null);
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
                self.filter_life(data['filter_life']);
                self.duty(data['pwm_duty_cycle']);
                if (data['sgp_raw'] > 0) {
                    self.sgp_raw(data['sgp_raw']);
                }
                if (data['sgp_index'] > 0) {
                    self.sgp_index(data['sgp_index']);
                }
                if (data['temperature'] > 0) {
                    self.temperature(data['temperature']);
                }
                if (data['relative_humidity'] > 0) {
                    self.relative_humidity(data['relative_humidity']);
                }
            });
        }

        self.getHistory = () => {
            $.getJSON("/plugin/airfilter/history", (data) => {
                if (data.history.length <= 0) {
                    return;
                }
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
            const red = 15 - Math.round((index - self.indexMin) / (self.indexMax - self.indexMin) * 7);
            const color = (15 << 8) + (red << 4) + red;
            const colorString = '#' + color.toString(16);
            console.log(colorString);
            return colorString;
        };

        self.rawColor = (raw) => {
            const red = 8 + Math.round((raw - self.rawMin) / (self.rawMax - self.rawMin) * 7);
            const color = (15 << 8) + (red << 4) + red;
            const colorString = '#' + color.toString(16);
            console.log(colorString);
            return colorString;
        };

        self.setDuty = () => {
            const request = {"duty": self.duty};
            $.ajax({
                url: "/plugin/airfilter/set_duty",
                type: "POST",
                data: ko.toJSON(request),
                contentType:"application/json; charset=utf-8",
                dataType:"json",
                success: () => {
                    $("#set-duty").css("background-color", "");
                },
                error: () => {
                    $("#set-duty").css("background-color", "#F88");
                }
            });
        }
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
