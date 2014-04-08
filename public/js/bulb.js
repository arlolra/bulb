/*global _ */
;(function () {
	"use strict";
	var graph;

	function setupGraph(timeBase) {
		graph = new Rickshaw.Graph({
		    element: document.querySelector("#chart"),
			renderer: "line",
		    series: new Rickshaw.Series.FixedDuration([
					{ color: "red", name: "read" },
					{ color: "green", name: "written" }
				], null, {
					timeInterval: 1000,
					maxDataPoints: 100,
					timeBase: timeBase
			})
		});
		graph.render();
	}

	function updateGraph(data) {
		// use the first timestamp as the base
		if ( !graph ) {
			setupGraph(data.arrived_at);
		}

		graph.series.addData({
			read: data.read,
			written: data.written 
		}, data.arrived_at);
		graph.update();
	}

	_.templateSettings = {
		evaluate : /\{\[(.+?)\]\}/g,
		interpolate : /\{\{(.+?)\}\}/g
	};

	function renderInfo(data) {
		var elt = document.getElementById("info"),
			tmpl = document.getElementById("info-template").text;
		tmpl = _.template(tmpl);
		elt.innerHTML = tmpl({ data: data });
	}

	var ws = new WebSocket("ws://localhost:9000/ws");

	ws.onmessage = function (e) {
		var msg = JSON.parse(e.data);
		switch( msg.type ) {
		case "bw":
			updateGraph(msg.data);
			break;
		case "info":
			renderInfo(msg.data);
			break;
		default:
			console.log(msg);
		}
	};

}());