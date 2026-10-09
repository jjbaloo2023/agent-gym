# Data provenance and training boundaries

This project begins as a scientific agent evaluation laboratory. Training export is not implemented and checkpoints default to training eligibility "unreviewed".

For every source and derived artifact record: human/solver/provider origin, provider and model version where applicable, input license, rights holder, intended use, verification result, split, and permitted training destination. Separating files does not remove provider-output influence from a derived artifact.

Prefer owned human demonstrations, rights-cleared domain data, and independently validated solver results for reusable datasets. Do not automatically turn evaluation traces into training corpora.

## OpenAI
Reviewed official sources on 2026-10-08:
- https://openai.com/policies/services-agreement/
- https://openai.com/policies/terms-of-use/
- https://openai.com/index/api-model-distillation/
- https://developers.openai.com/learn/fine-tuning

The Services Agreement restricts using Output to develop competing AI models except its defined permitted exceptions, including customization through OpenAI's services. OpenAI also documents distillation within its own platform. This does not establish blanket permission to train third-party models from OpenAI traces.

Use authorized API access, respect rate/usage limits, and review the applicable account agreement and intended training destination before export. Evaluation, workflow/prompt optimization, and updating model weights are distinct activities. This design cannot guarantee account enforcement outcomes.

A future exporter must require an explicit destination and a reviewed eligibility decision; preserve provenance, exclude unapproved traces, and log the decision. No provider output or private workflow data belongs in Git by default.
