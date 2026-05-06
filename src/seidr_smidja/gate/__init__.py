"""
Gate — the Compliance Gate.

The validation layer. Every .vrm output passes through the Gate before it is
delivered. The Gate validates against:
  - VRChat requirements: polygon budgets, bone structure, viseme coverage,
    material count, texture size limits.
  - VTube Studio requirements: VRM spec version, expression/blendshape coverage,
    lookat configuration.

Outputs that fail are not delivered — they return structured failure reports.
A blade that cannot cut has not been made.

Compliance rules live in YAML data files. None are hardcoded here.

Public surface: see INTERFACE.md in this directory.
"""
