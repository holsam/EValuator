// Implements Streamlit's iframe postMessage component protocol directly rather than using streamlit-component-lib npm package to avoid adding JS build toolchain

(function () {
  function sendToStreamlit(type, data) {
    window.parent.postMessage(Object.assign({ type: type, isStreamlitMessage: true }, data), "*");
  }
  function setComponentValue(value) {
    sendToStreamlit("streamlit:setComponentValue", { value: value, dataType: "json" });
  }
  function setFrameHeight(height) {
    sendToStreamlit("streamlit:setFrameHeight", { height: height });
  }

  function render(args) {
    const figure = JSON.parse(args.figure);
    const div = document.getElementById("plot");

    figure.layout = figure.layout || {};
    figure.layout.scene = figure.layout.scene || {};
    // Force camera prop into non-interactive panels so they track the main view orientation
    if (args.camera && !args.interactive) {
      figure.layout.scene.camera = args.camera;
    }
    figure.layout.scene.dragmode = args.interactive ? "orbit" : false;
    figure.layout.margin = figure.layout.margin || { l: 0, r: 0, t: 0, b: 0 };
    // No explicit camera so need Plotly to provide user's current orientation across re-renders
    figure.layout.uirevision = "viewer";

    const config = { displayModeBar: !!args.interactive, scrollZoom: !!args.interactive };

    // Force a full purge and rebuild of Plotly.react buffers when gl3d trace type changes on same div
    const traceSignature = figure.data.map(function (t) { return t.type; }).join(",");
    const typeChanged = div.__lastTraceSignature !== undefined && div.__lastTraceSignature !== traceSignature;
    div.__lastTraceSignature = traceSignature;

    const plotPromise = typeChanged
      ? (Plotly.purge(div), div.__evaluatorBound = false, Plotly.newPlot(div, figure.data, figure.layout, config))
      : Plotly.react(div, figure.data, figure.layout, config);

    plotPromise.then(function () {
      setFrameHeight(div.offsetHeight || 420);

      // As above purging also removes Plotly's internal event system, rewire listeners
      if (args.interactive && !div.__evaluatorBound) {
        div.__evaluatorBound = true;
        // Tag events with fresh ids so Python can distinguish new clicks from re-returned values
        div.on("plotly_click", function (data) {
          if (!data || !data.points || !data.points.length) return;
          const shiftKey = !!(data.event && data.event.shiftKey);
          setComponentValue({ clicked_curve: data.points[0].curveNumber, shift_key: shiftKey, camera: null, event_id: Date.now() + Math.random() });
        });
        div.on("plotly_relayout", function (eventData) {
          const camera = eventData["scene.camera"];
          if (!camera) return;
          // Add small delay before syncing mini panels so it's not triggered by each step during zooming
          clearTimeout(div.__relayoutDebounce);
          div.__relayoutDebounce = setTimeout(function () {
            setComponentValue({ clicked_curve: null, camera: camera, event_id: Date.now() + Math.random() });
          }, 180);
        });
      }
    });
  }

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "streamlit:render") return;
    render(event.data.args);
  });

  sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
  setFrameHeight(420);
})();