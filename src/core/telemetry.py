from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import logging

_logger = logging.getLogger("CodeCortex.Telemetry")

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
    )
    trace.set_tracer_provider(provider)
    _logger.info("OpenTelemetry tracing initialized (endpoint: http://localhost:4317)")
except Exception as e:
    _logger.warning(f"OpenTelemetry unavailable, tracing disabled: {e}")
    trace.set_tracer_provider(TracerProvider())
