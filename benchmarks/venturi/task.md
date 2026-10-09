# Common CAD attempt task

Use only the approved PDF page image supplied for the attempt. Interpret its Venturi geometry and use the scientific MCP to build an axisymmetric body matching the source. Explain inconsistent labels and every assumption. Exclude pressure taps and flanges, which the current bounded tool does not support. Do not run CFD.

Use a dedicated attempt workspace; do not read other attempts or reference solutions. Use list_tools, build_venturi, mesh_venturi, and inspect_design as needed. One final candidate. Maximum 12 budgeted tool-helper invocations and 15 minutes from first invocation. Scientific operations are serialized through a shared lock. Write a report describing source interpretation, assumptions, artifact paths, validity, mesh outcome, and verification limits. Do not assign human scores.

The input image is artifacts/venturi-benchmark/input/page-35.png. Labels A/B/C are randomized relative to model-list order and remain hidden during scoring. The actual invocation ledger records tool arguments, results/errors and start/finish times; it does not include model-token usage or the full model conversation.
