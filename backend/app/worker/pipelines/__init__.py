# Pipeline Steps
# P0 Fix: Lazy imports to prevent psycopg2 dependency on module access
# This allows importing submodules without DB driver installed

_LAZY_IMPORTS = {
    # snapshot.py
    "SnapshotPipeline": "app.worker.pipelines.snapshot",
    "NoSnapshotError": "app.worker.pipelines.snapshot",
    "NoCorporationError": "app.worker.pipelines.snapshot",
    # doc_ingest.py
    "DocIngestPipeline": "app.worker.pipelines.doc_ingest",
    "DocumentProcessingError": "app.worker.pipelines.doc_ingest",
    # context.py
    "ContextPipeline": "app.worker.pipelines.context",
    # external_search.py
    "ExternalSearchPipeline": "app.worker.pipelines.external_search",
    # signal_extraction.py
    "SignalExtractionPipeline": "app.worker.pipelines.signal_extraction",
    # validation.py
    "ValidationPipeline": "app.worker.pipelines.validation",
    # deduplication.py
    "DeduplicationPipeline": "app.worker.pipelines.deduplication",
    "deduplicate_within_batch": "app.worker.pipelines.deduplication",
    # index.py
    "IndexPipeline": "app.worker.pipelines.index",
    "DuplicateSignalError": "app.worker.pipelines.index",
    # insight.py
    "InsightPipeline": "app.worker.pipelines.insight",
    # expert_insight.py
    "ExpertInsightPipeline": "app.worker.pipelines.expert_insight",
    "generate_actionable_checklist": "app.worker.pipelines.expert_insight",
    "generate_early_warning_dashboard": "app.worker.pipelines.expert_insight",
    "get_quality_report": "app.worker.pipelines.expert_insight",
    # corp_profiling.py
    "CorpProfilingPipeline": "app.worker.pipelines.corp_profiling",
    "get_corp_profiling_pipeline": "app.worker.pipelines.corp_profiling",
    "CorpProfileValidator": "app.worker.pipelines.corp_profiling",
    "EnvironmentQuerySelector": "app.worker.pipelines.corp_profiling",
    "ProfileEvidenceCreator": "app.worker.pipelines.corp_profiling",
    # signal_agents (Sprint 2)
    "BaseSignalAgent": "app.worker.pipelines.signal_agents",
    "DirectSignalAgent": "app.worker.pipelines.signal_agents",
    "IndustrySignalAgent": "app.worker.pipelines.signal_agents",
    "EnvironmentSignalAgent": "app.worker.pipelines.signal_agents",
    "SignalAgentOrchestrator": "app.worker.pipelines.signal_agents",
}


def __getattr__(name):
    """Lazy import to prevent psycopg2 dependency on module access."""
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SnapshotPipeline",
    "NoSnapshotError",
    "NoCorporationError",
    "DocIngestPipeline",
    "DocumentProcessingError",
    "ContextPipeline",
    "ExternalSearchPipeline",
    "SignalExtractionPipeline",
    "ValidationPipeline",
    "DeduplicationPipeline",
    "deduplicate_within_batch",
    "IndexPipeline",
    "DuplicateSignalError",
    "InsightPipeline",
    # Expert Insight (v2.0 - 4-Layer Architecture)
    "ExpertInsightPipeline",
    "generate_actionable_checklist",
    "generate_early_warning_dashboard",
    "get_quality_report",
    # Corp Profiling (Anti-Hallucination)
    "CorpProfilingPipeline",
    "get_corp_profiling_pipeline",
    "CorpProfileValidator",
    "EnvironmentQuerySelector",
    "ProfileEvidenceCreator",
    # Sprint 2: Signal Multi-Agent Architecture (ADR-009)
    "BaseSignalAgent",
    "DirectSignalAgent",
    "IndustrySignalAgent",
    "EnvironmentSignalAgent",
    "SignalAgentOrchestrator",
]
