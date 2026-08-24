from __future__ import annotations

import logging

from meridian.observability.export import export_span
from meridian.observability.spans import span


def test_export_span_logs_a_structured_record(caplog):
    with caplog.at_level(logging.INFO, logger="meridian.observability"):
        with span("do_work", capability="chat") as s:
            pass
        export_span(s)

    records = [r for r in caplog.records if r.message == "span"]
    assert len(records) == 1
    assert records[0].span_id == s.span_id
    assert records[0].span_name == "do_work"
    assert records[0].status == "ok"


def test_export_span_never_raises_even_with_a_broken_attribute(monkeypatch):
    import meridian.observability.export as export_module

    def _boom(*args, **kwargs):
        raise RuntimeError("logging backend down")

    monkeypatch.setattr(export_module.logger, "info", _boom)

    with span("do_work") as s:
        pass

    export_span(s)  # must not raise
