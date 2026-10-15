# Ground Truth Validation Report

**Generated:** 2026-08-19T08:31:19.414029+00:00Z
**Total Questions Evaluated:** 105
**Total Questions Validated:** 105
**Total Questions Rejected:** 0
**Validation Success Rate:** 100.0%

## Validation Criteria Checklist
1. ✅ `document_id` exists in MongoDB
2. ✅ Document belongs to frozen 20-doc corpus
3. ✅ Document status == `completed`
4. ✅ Chunk exists in ChromaDB `building_documents`
5. ✅ Chunk belongs to target `document_id`
6. ✅ `chunk_index` matches metadata
7. ✅ Page metadata matches stored page number
8. ✅ `exact_ground_truth_evidence` is present verbatim in ChromaDB chunk
9. ✅ Expected entities exist in Neo4j (when specified)
10. ✅ Expected relationships exist in Neo4j (when specified)

## Validation Summary by Question

| Question ID | Domain | Difficulty | Status | Rejection Reasons |
|---|---|---|---|---|
| `Q001` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q002` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q003` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q004` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q005` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q006` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q007` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q008` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q009` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q010` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q011` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q012` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q013` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q014` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q015` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q016` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q017` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q018` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q019` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q020` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q021` | Building Guidelines, Codes & Facility Specifications | easy | ✅ VALIDATED | None |
| `Q022` | Building Guidelines, Codes & Facility Specifications | medium | ✅ VALIDATED | None |
| `Q023` | Building Guidelines, Codes & Facility Specifications | hard | ✅ VALIDATED | None |
| `Q024` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q025` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q026` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q027` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q028` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q029` | Concrete Durability & Carbonation | hard | ✅ VALIDATED | None |
| `Q030` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q031` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q032` | Concrete Durability & Carbonation | hard | ✅ VALIDATED | None |
| `Q033` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q034` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q035` | Concrete Durability & Carbonation | hard | ✅ VALIDATED | None |
| `Q036` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q037` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q038` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q039` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q040` | Concrete Durability & Carbonation | hard | ✅ VALIDATED | None |
| `Q041` | Concrete Durability & Carbonation | easy | ✅ VALIDATED | None |
| `Q042` | Concrete Durability & Carbonation | medium | ✅ VALIDATED | None |
| `Q043` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q044` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q045` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q046` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q047` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q048` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q049` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q050` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q051` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q052` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q053` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q054` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q055` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q056` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q057` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q058` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q059` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q060` | Seismic & Structural Retrofitting | medium | ✅ VALIDATED | None |
| `Q061` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q062` | Seismic & Structural Retrofitting | easy | ✅ VALIDATED | None |
| `Q063` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q064` | Geotechnical & Foundation Engineering | medium | ✅ VALIDATED | None |
| `Q065` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |
| `Q066` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q067` | Geotechnical & Foundation Engineering | medium | ✅ VALIDATED | None |
| `Q068` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |
| `Q069` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q070` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q071` | Geotechnical & Foundation Engineering | medium | ✅ VALIDATED | None |
| `Q072` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |
| `Q073` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q074` | Geotechnical & Foundation Engineering | medium | ✅ VALIDATED | None |
| `Q075` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |
| `Q076` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q077` | Geotechnical & Foundation Engineering | medium | ✅ VALIDATED | None |
| `Q078` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |
| `Q079` | Geotechnical & Foundation Engineering | easy | ✅ VALIDATED | None |
| `Q080` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q081` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q082` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q083` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q084` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q085` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q086` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q087` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q088` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q089` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q090` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q091` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q092` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q093` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q094` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q095` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q096` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q097` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q098` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q099` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q100` | Inspection & Structural Health Monitoring | easy | ✅ VALIDATED | None |
| `Q101` | Inspection & Structural Health Monitoring | medium | ✅ VALIDATED | None |
| `Q102` | Concrete Durability & Carbonation | hard | ✅ VALIDATED | None |
| `Q103` | Seismic & Structural Retrofitting | hard | ✅ VALIDATED | None |
| `Q104` | Inspection & Structural Health Monitoring | hard | ✅ VALIDATED | None |
| `Q105` | Geotechnical & Foundation Engineering | hard | ✅ VALIDATED | None |