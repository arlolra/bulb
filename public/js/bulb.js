/*global _ */
;(function () {
	"use strict";
	var graph;

	function setupGraph(timeBase) {
		graph = new Rickshaw.Graph({
		    element: document.querySelector("#chart"),
			renderer: 'area',
			height: 200,
		    series: new Rickshaw.Series.FixedDuration([
					{ color: "green", name: "read" },
					{ color: "#999", name: "written" }
				], null, {
					timeInterval: 1000,
					maxDataPoints: 100,
					timeBase: timeBase
			})
		});
		graph.render();
		var legend = new Rickshaw.Graph.Legend({
		    graph: graph,
		    element: document.querySelector("#legend")
		});
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