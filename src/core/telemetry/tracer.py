"""
OpenTelemetry setup – lazy initialization, no module-level side effects.

:project: CodeCortex
:package: Core.Telemetry.Tracer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("CodeCortex.Core.Telemetry")

_tracer_provider: Optional[object] = None
_meter_provider: Optional[object] = None

def get_tracer_provider() -> Optional[object]:
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider = TracerProvider()
        exporter = OTLPSpanExporter()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer_provider = provider
        logger.info(
            "[TELEMETRY_INIT] OTLP exporter configured",
            extra={"event_code": "TELEMETRY_INIT"},
        )
        return provider
    except ImportError:
        logger.debug(
            "[TELEMETRY_SKIP] OpenTelemetry not installed",
            extra={"event_code": "TELEMETRY_SKIP"},
        )
        return None
    except Exception as e:
        logger.warning(
            "[TELEMETRY_FAIL] init error: %s",
            str(e),
            extra={"event_code": "TELEMETRY_FAIL", "error": str(e)},
        )
        return None

def get_meter_provider() -> Optional[object]:
    global _meter_provider
    if _meter_provider is not None:
        return _meter_provider

    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

        exporter = OTLPMetricExporter()
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        _meter_provider = provider
        logger.info(
            "[METRICS_INIT] OTLP exporter configured",
            extra={"event_code": "METRICS_INIT"},
        )
        return provider
    except ImportError:
        logger.debug(
            "[METRICS_SKIP] OpenTelemetry not installed",
            extra={"event_code": "METRICS_SKIP"},
        )
        return None
    except Exception as e:
        logger.warning(
            "[METRICS_FAIL] init error: %s",
            str(e),
            extra={"event_code": "METRICS_FAIL", "error": str(e)},
        )
        return None

def start_span(name: str, **attributes):
    provider = get_tracer_provider()
    if provider is None:
        return None

    tracer = provider.get_tracer(__name__)
    span = tracer.start_span(name)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    return span

def record_metric(name: str, value: float, **attributes):
    provider = get_meter_provider()
    if provider is None:
        return

    meter = provider.get_meter(__name__)
    counter = meter.create_counter(name)
    counter.add(value, attributes)
