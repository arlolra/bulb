/*global _ */
;(function () {
	"use strict";

	var graph;
	function setupGraph(timeBase) {
		graph = new Rickshaw.Graph({
			element: document.querySelector("#chart"),
			renderer: 'area',
			height: 200,
			stroke: true,
			series: new Rickshaw.Series.FixedDuration([
					{ color: "plum", name: "read" },
					{ color: "whitesmoke", name: "written" }
				], null, {
					timeInterval: 1000,
					maxDataPoints: 100,
					timeBase: timeBase
			})
		});
		var legend = new Rickshaw.Graph.Legend({
		    graph: graph,
		    element: document.querySelector("#legend")
		});
		function formatter(series, x, y) {
			return y + " bytes";
		}
		var yAxis = new Rickshaw.Graph.Axis.Y({
		    graph: graph,
			tickFormat: formatter.bind(null, null, null)
		});
		var hoverDetail = new Rickshaw.Graph.HoverDetail({
			graph: graph,
			formatter: formatter
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
			tmpl = _.template(document.getElementById("info-template").text);
		elt.innerHTML = tmpl({ data: data });
	}

	var max_logs = 10,
		log = document.getElementById("logs"),
		log_tmpl = _.template(document.getElementById("log-template").text);
	function renderLog(data) {
		var li = document.createElement("li");
		li.innerHTML = log_tmpl({
			level: data.level.toLowerCase(),
			text: data.text
		});
		log.insertBefore(li, log.firstChild);
		log.childNodes.length = max_logs;
		while ( log.childNodes.length > max_logs ) {
			log.removeChild(log.childNodes[max_logs + 1]);
		}
	}

	var ws = new WebSocket("ws://" + window.location.host + "/ws");

	ws.onmessage = function (e) {
		var msg = JSON.parse(e.data);
		switch( msg.type ) {
		case "bw":
			updateGraph(msg.data);
			break;
		case "info":
			renderInfo(msg.data);
			break;
		case "log":
			renderLog(msg.data);
			break;
		default:
			console.log(msg);
		}
	};

}());