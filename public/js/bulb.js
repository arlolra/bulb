;(function () {
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

	var ws = new WebSocket("ws://localhost:9000/ws");

	ws.onmessage = function (e) {
		var data = JSON.parse(e.data);

		// use the first timestamp as the base
		if ( !graph ) {
			setupGraph(data.arrived_at);
		}

		graph.series.addData({
			read: data.read,
			written: data.written 
		}, data.arrived_at);
		graph.update();
	};

}());