# First approved-drawing run

Status: awaiting human scores. One independent attempt each was dispatched to the requested GPT-6 Luna, GPT-6.1 Sol, and GPT-6 Astra aliases with medium reasoning. Exact backend snapshots and token/cost usage were not available from the subagent interface.

Input: approved university thermal-fluid manual, PDF page 35, Figure 4.3 and its accompanying dimension table. The source checksum is in results-summary.json. The downloaded PDF and extracted page remain in ignored local artifacts; they are not redistributed in Git.

All three attempts selected the same dimensions and wall-thickness assumption. Each used four budgeted tool-helper invocations with no recorded tool error. All CAD and mesh checks passed. The parent independently reopened native CAD, checked valid single solids, verified fluid STEP volume against an analytical cylinder/frustum formula, and verified spreadsheet edits propagate to geometry. Agent-selected mesh size differs, so cell counts are not a model-quality ranking.

The blinded packet is artifacts/venturi-benchmark/review/index.html. Serve that directory only, bound to localhost, for scoring. It contains source page, actual STL previews, reports, native/exchange/mesh artifacts, and blank scoring fields. The private label-to-model mapping remains outside the served packet in ignored artifacts. Scores are entered by the user and exported as CSV; the web page does not submit them to the agent automatically.

This is a geometry-interpretation and structured-tool-use test: all models used the same parametric CAD generator. With one attempt each and a simple constrained family, this does not establish a general CAD capability ranking.

No CFD solver or overnight run has started. Human scores and a selected candidate are still required; then define flow conditions and validate a short case before a longer solve.
