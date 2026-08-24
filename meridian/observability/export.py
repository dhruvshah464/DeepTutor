"""
Span export: a structured-log sink always, OpenTelemetry if installed.

OpenTelemetry is deliberately not a hard dependency — declaring
opentelemetry-api/-sdk would add real weight to every install for a
feature only some deployments want. export_span() always logs a
structured record (a real, durable sink with zero extra dependencies);
it additionally forwards to OTel when the packages are importable,
exactly the same optional-dependency pattern this project already uses
for tiktoken/passlib.
"""

from __future__ import annotations

import logging

from meridian.observability.spans import Span

logger = logging.getLogger("meridian.observability")

try:
    from opentelemetry import trace as _otel_trace

    _OTEL_TRACER = _otel_trace.get_tracer("meridian")
except Exception:  # pragma: no cover - opentelemetry is an optional dependency
    _OTEL_TRACER = None


def export_span(span: Span) -> None:
    """Emit a completed span. Non-fatal: never raises into the caller's turn."""
    try:
        # "name" (and a handful of other keys) are reserved LogRecord
        # attributes — passing them via `extra` raises
        # `KeyError: "Attempt to overwrite 'name' in LogRecord"`, so the
        # span's own name is prefixed to avoid the collision.
        logger.info(
            "span",
            extra={
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "parent_span_id": span.parent_span_id,
                "span_name": span.name,
                "status": span.status,
                "duration_ms": span.duration_ms,
                "attributes": span.attributes,
                "error": span.error,
            },
        )
    except Exception:
        logger.debug("Failed to log span", exc_info=True)

    if _OTEL_TRACER is None:
        return
    try:
        _export_to_otel(span)
    except Exception:
        logger.debug("Failed to export span to OpenTelemetry", exc_info=True)


def _export_to_otel(span: Span) -> None:
    from opentelemetry.trace import Status, StatusCode

    with _OTEL_TRACER.start_as_current_span(span.name) as otel_span:
        for key, value in span.attributes.items():
            try:
                otel_span.set_attribute(key, value)
            except Exception:
                otel_span.set_attribute(key, str(value))
        otel_span.set_attribute("meridian.span_id", span.span_id)
        otel_span.set_attribute("meridian.trace_id", span.trace_id)
        if span.status == "error":
            otel_span.set_status(Status(StatusCode.ERROR, span.error or ""))
        else:
            otel_span.set_status(Status(StatusCode.OK))
