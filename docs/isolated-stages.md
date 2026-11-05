# Independently run FlowValue stages
## Entry engineering workflow (current behaviour)

Entry now has one **Run Engineering & Price Equipment** action. It loads a selected workbook (or reuses the current one), then explicitly runs Engineering data followed by Equipment. Both existing runners remain canonical. The shared register feeds Engineering data and Equipment pages; equipment output includes sizing and available purchase/installation costs. Failed extraction stops this handoff; unpriced items remain visible. The AI checkbox applies to this two-stage workflow. No CAPEX, OPEX, Revenue or Financial runner is invoked.

`POST /api/assessments/{id}/engineering/run` queues this explicit workflow. The individual-stage API remains available for focused reruns. Entry no longer shows separate Engineering data and Equipment run buttons. Other stages still require an explicit run, and ordinary page views do not execute engines. Older descriptions below of a source-only Entry button describe the previous isolated configuration; they are superseded by this section.


The founder chose disconnected execution: each stage is selected separately. Dependencies are data requirements, not instructions to start another stage.

1. On Entry, choose the workbook and enter the process and Revenue Box text. **Run Assessment** loads the source only.
2. Use **Run Engineering data** to parse/review the workbook. No equipment costs or economics run.
3. **Run Equipment** requires Engineering data. It performs only the equipment block's sizing and costing.
4. **Run CAPEX** requires saved Equipment output. It does not reprice equipment.
5. **Run Revenue** requires Engineering data, its own commercial inputs and user approval. It does not need CAPEX/OPEX when a price basis is supplied directly.
6. **Run OPEX** uses saved Engineering data and explicitly declares any selected CAPEX- or Revenue-dependent factors. Itemised expenses can run without either monetary block.
7. **Run Financial model** consumes the saved, current results of CAPEX, Revenue and OPEX. It does not rerun them.

The same stage button appears on each stage's page. A missing prerequisite says **Data required**. Changed inputs mark affected results **Rerun required** without calculating them. Other independent outputs stay available.

The frontend's public page entry points and business views live in `frontend/src/blocks/{entry,engineering_data,equipment,capex,opex,revenue,financial,overview,uncertainty}`. Shared navigation, project loading and form infrastructure live in `blocks/shared`. Old component import paths are compatibility facades, not duplicate implementations.

Backend execution contracts, responsibilities and dependency declarations are documented in [the block index](../backend/blocks/README.md). The existing numerical engine folders remain canonical.

This change isolates execution and source ownership; it does not establish engineering accuracy or implement missing costing correlations, VCOP/FCOP, new research methods or a new financial engine.
