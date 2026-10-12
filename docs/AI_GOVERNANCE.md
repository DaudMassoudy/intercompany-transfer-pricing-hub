# AI Governance — v2.0.0-rc.1

AI is advisory only.

The RC preserves deterministic backend ownership of TP/accounting calculations and provides an evidence-grounded explanation layer plus schema for versioned documents, evidence chunks and AI invocation metadata.

Any production RAG/model integration must:

- filter retrieval by tenant/client/entity/period/document permissions before generation;
- cite evidence;
- persist provider/model/prompt/retrieval metadata;
- expose missing/uncertain evidence;
- support AI OFF / local / approved enterprise-provider modes;
- undergo prompt-injection and source-grounding evaluation.

AI may not alter policies, authoritative calculations, approvals, journals, ERP postings or source financial records.
