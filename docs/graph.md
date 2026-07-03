# Knowledge graph

Every edge below is an **RDF predicate** drawn from a concept's typed
frontmatter relations — labels like `prov:wasDerivedFrom`, `dcterms:requires`,
or `lokf:measures` (compacted through the LOKF
[vocabulary](guide/relationships.md)). Plain markdown links in a concept's
*body* are **not** edges: only the typed relations that project to RDF triples
appear here, so this graph is exactly the concept-to-concept subset of the
[bundle's RDF projection](examples.md).

The data is the [Acme knowledge bundle](examples.md) — six concepts, eight
typed relations. Search dims non-matching nodes; the filters toggle node types
and predicates; click a node for its details.

<div class="lokf-graph">
  <div class="lokf-graph__controls">
    <input type="search" id="lokf-search" class="lokf-graph__search"
           placeholder="Search nodes by label…" autocomplete="off" />
    <div class="lokf-graph__filters">
      <fieldset id="lokf-type-filter" class="lokf-graph__fieldset">
        <legend>Node types</legend>
      </fieldset>
      <fieldset id="lokf-predicate-filter" class="lokf-graph__fieldset">
        <legend>Predicates</legend>
      </fieldset>
    </div>
  </div>
  <div class="lokf-graph__stage">
    <div id="lokf-cy" class="lokf-graph__canvas"></div>
    <aside id="lokf-detail" class="lokf-graph__detail" hidden>
      <button type="button" id="lokf-detail-close"
              class="lokf-graph__close" aria-label="Close">&times;</button>
      <h3 id="lokf-detail-title"></h3>
      <dl>
        <dt>Type</dt><dd id="lokf-detail-type"></dd>
        <dt>IRI</dt><dd id="lokf-detail-iri" class="lokf-graph__mono"></dd>
        <dt>Concept ID</dt><dd id="lokf-detail-cid" class="lokf-graph__mono"></dd>
      </dl>
      <a id="lokf-detail-src" href="#" rel="noopener">View source file →</a>
    </aside>
  </div>
</div>

<style>
.lokf-graph { margin: 1rem 0 2rem; }
.lokf-graph__controls {
  display: flex; flex-direction: column; gap: .6rem; margin-bottom: .8rem;
}
.lokf-graph__search {
  width: 100%; padding: .5rem .7rem; font-size: .8rem;
  color: var(--md-default-fg-color);
  background: var(--md-default-bg-color);
  border: 1px solid var(--md-default-fg-color--lighter);
  border-radius: .3rem;
}
.lokf-graph__filters { display: flex; flex-wrap: wrap; gap: .8rem; }
.lokf-graph__fieldset {
  flex: 1 1 12rem; min-width: 11rem; padding: .4rem .7rem .6rem;
  border: 1px solid var(--md-default-fg-color--lighter); border-radius: .3rem;
}
.lokf-graph__fieldset legend {
  font-size: .65rem; font-weight: 700; letter-spacing: .04em;
  text-transform: uppercase; color: var(--md-default-fg-color--light);
  padding: 0 .3rem;
}
.lokf-graph__fieldset label {
  display: flex; align-items: center; gap: .35rem;
  font-size: .74rem; line-height: 1.7; cursor: pointer;
}
.lokf-graph__swatch {
  width: .7rem; height: .7rem; border-radius: 50%; flex: none;
  border: 1px solid var(--md-default-fg-color--lighter);
}
.lokf-graph__stage { position: relative; }
.lokf-graph__canvas {
  width: 100%; height: 560px;
  border: 1px solid var(--md-default-fg-color--lighter); border-radius: .3rem;
  background: var(--md-code-bg-color);
}
.lokf-graph__detail {
  position: absolute; top: .6rem; right: .6rem; width: min(19rem, 80%);
  padding: .8rem 1rem 1rem; font-size: .78rem;
  color: var(--md-default-fg-color);
  background: var(--md-default-bg-color);
  border: 1px solid var(--md-default-fg-color--lighter);
  border-radius: .4rem; box-shadow: var(--md-shadow-z2);
}
.lokf-graph__detail h3 { margin: 0 2rem .6rem 0; font-size: .95rem; }
.lokf-graph__detail dl { display: grid; grid-template-columns: auto 1fr;
  gap: .1rem .6rem; margin: 0 0 .7rem; }
.lokf-graph__detail dt { font-weight: 700;
  color: var(--md-default-fg-color--light); }
.lokf-graph__detail dd { margin: 0; word-break: break-all; }
.lokf-graph__mono { font-family: var(--md-code-font-family, monospace);
  font-size: .72rem; }
.lokf-graph__close {
  position: absolute; top: .3rem; right: .4rem; border: 0; background: none;
  font-size: 1.3rem; line-height: 1; cursor: pointer;
  color: var(--md-default-fg-color--light);
}
</style>

<script src="../assets/js/cytoscape.min.js"></script>
<script>
(function () {
  var mount = document.getElementById("lokf-cy");
  if (!mount || typeof cytoscape === "undefined") { return; }
  // Small type -> color palette; nodes without a known type fall through.
  var PALETTE = [
    "#5b8def", "#e8833a", "#2ea77d", "#c1558b",
    "#9b6dd6", "#d2b13a", "#4bacc6", "#d05b5b"
  ];
  var SRC_BASE =
    "https://github.com/nicholsn/lokf/tree/main/examples/acme-knowledge/";

  fetch("../assets/graph.json")
    .then(function (r) { return r.json(); })
    .then(function (graph) { render(graph); })
    .catch(function (e) {
      mount.textContent = "Could not load graph data: " + e;
    });

  function render(graph) {
    var types = [];
    graph.nodes.forEach(function (n) {
      if (types.indexOf(n.data.type) === -1) { types.push(n.data.type); }
    });
    var colorOf = {};
    types.forEach(function (t, i) { colorOf[t] = PALETTE[i % PALETTE.length]; });
    graph.nodes.forEach(function (n) { n.data.color = colorOf[n.data.type]; });

    var predicates = [];
    graph.edges.forEach(function (e) {
      if (predicates.indexOf(e.data.predicate) === -1) {
        predicates.push(e.data.predicate);
      }
    });

    // Resolve theme colors through a DOM probe: Material publishes modern
    // hsla(Ndeg, ...) values that cytoscape's style parser rejects, while a
    // computed style read always yields rgb()/rgba().
    var probe = document.createElement("span");
    probe.style.display = "none";
    document.body.appendChild(probe);
    function themeColor(varName, fallback) {
      probe.style.color = "";
      probe.style.color = "var(" + varName + ")";
      var v = getComputedStyle(probe).color;
      return v && v !== "" ? v : fallback;
    }
    var fg = themeColor("--md-default-fg-color", "#000");
    var faint = themeColor("--md-default-fg-color--light", "#666");
    var bg = themeColor("--md-default-bg-color", "#fff");
    probe.remove();

    var cy = cytoscape({
      container: mount,
      elements: graph,
      layout: { name: "cose", padding: 30, animate: false,
                nodeRepulsion: 9000, idealEdgeLength: 130 },
      style: [
        { selector: "node", style: {
            "background-color": "data(color)",
            "label": "data(label)",
            "color": fg,
            "font-size": "11px",
            "text-wrap": "wrap", "text-max-width": "120px",
            "text-valign": "bottom", "text-margin-y": 4,
            "width": 26, "height": 26,
            "border-width": 2, "border-color": bg
        } },
        { selector: "edge", style: {
            "label": "data(predicate)",
            "font-size": "8px",
            "color": faint,
            "text-background-color": bg,
            "text-background-opacity": 0.85,
            "text-background-padding": 2,
            "width": 1.5,
            "line-color": faint,
            "target-arrow-color": faint,
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.9,
            "curve-style": "bezier"
        } },
        { selector: ".lokf-dim", style: { "opacity": 0.12 } },
        { selector: ".lokf-hide", style: { "display": "none" } },
        { selector: "node:selected", style: {
            "border-width": 3, "border-color": fg } }
      ]
    });

    buildTypeFilter(cy, types, colorOf);
    buildPredicateFilter(cy, predicates);
    wireSearch(cy);
    wireDetail(cy);
  }

  function buildTypeFilter(cy, types, colorOf) {
    var box = document.getElementById("lokf-type-filter");
    types.forEach(function (t) {
      var label = document.createElement("label");
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = true; cb.value = t;
      cb.addEventListener("change", function () { applyFilters(cy); });
      var sw = document.createElement("span");
      sw.className = "lokf-graph__swatch";
      sw.style.background = colorOf[t];
      label.appendChild(cb); label.appendChild(sw);
      label.appendChild(document.createTextNode(t));
      box.appendChild(label);
    });
  }

  function buildPredicateFilter(cy, predicates) {
    var box = document.getElementById("lokf-predicate-filter");
    predicates.forEach(function (p) {
      var label = document.createElement("label");
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = true; cb.value = p;
      cb.dataset.predicate = p;
      cb.addEventListener("change", function () { applyFilters(cy); });
      label.appendChild(cb);
      label.appendChild(document.createTextNode(" " + p));
      box.appendChild(label);
    });
  }

  function checkedValues(sel) {
    var out = {};
    document.querySelectorAll(sel).forEach(function (cb) {
      out[cb.value] = cb.checked;
    });
    return out;
  }

  function applyFilters(cy) {
    var okType = checkedValues("#lokf-type-filter input");
    var okPred = checkedValues("#lokf-predicate-filter input");
    cy.batch(function () {
      cy.nodes().forEach(function (n) {
        n.toggleClass("lokf-hide", okType[n.data("type")] === false);
      });
      cy.edges().forEach(function (e) {
        var hidden = okPred[e.data("predicate")] === false ||
          e.source().hasClass("lokf-hide") || e.target().hasClass("lokf-hide");
        e.toggleClass("lokf-hide", hidden);
      });
    });
  }

  function wireSearch(cy) {
    var input = document.getElementById("lokf-search");
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      cy.batch(function () {
        cy.nodes().forEach(function (n) {
          var hit = !q || (n.data("label") || "").toLowerCase().indexOf(q) >= 0;
          n.toggleClass("lokf-dim", !hit);
        });
      });
    });
  }

  function wireDetail(cy) {
    var panel = document.getElementById("lokf-detail");
    var close = document.getElementById("lokf-detail-close");
    cy.on("tap", "node", function (evt) {
      var d = evt.target.data();
      document.getElementById("lokf-detail-title").textContent = d.label;
      document.getElementById("lokf-detail-type").textContent = d.type;
      document.getElementById("lokf-detail-iri").textContent = d.id;
      document.getElementById("lokf-detail-cid").textContent = d.concept_id;
      var src = document.getElementById("lokf-detail-src");
      src.href = SRC_BASE + d.concept_id + ".md";
      panel.hidden = false;
    });
    cy.on("tap", function (evt) {
      if (evt.target === cy) { panel.hidden = true; }
    });
    close.addEventListener("click", function () { panel.hidden = true; });
  }
})();
</script>
