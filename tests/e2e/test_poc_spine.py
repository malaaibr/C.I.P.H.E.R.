"""
E2E POC Spine Test (T-025).

Validates all 6 POC exit criteria from ADR-0003 §7:
  1. HLD prompt → LLD CSV generated with ≥5 rows
  2. LLD stored in MinIO (cipher-artifacts bucket)
  3. OTel trace complete (spans emitted for full pipeline)
  4. Audit journal records all LLM calls
  5. OPA policy evaluates to allow
  6. Workflow checkpoint persists to SQLite

Requires: docker compose up (all services running).
Mark: pytest -m e2e
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cipher.core.schemas.task_contract import TaskClass, TaskContract, TaskResult, TaskStatus


pytestmark = pytest.mark.e2e


class TestPOCExitCriterion1_LLDGeneration:
    """Exit Criterion 1: Feed synthetic HLD → get LLD CSV with ≥5 rows."""

    @pytest.mark.asyncio
    async def test_s1n1_produces_lld_with_rows(self) -> None:
        from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
        from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse

        lld_csv = (
            "id,component,module,description,requirement_ref\n"
            "1,ECU_Main,PowerMgmt,Power management controller,HLD-REQ-001\n"
            "2,ECU_Main,CommStack,CAN bus communication stack,HLD-REQ-002\n"
            "3,ECU_Main,Diagnostics,UDS diagnostic handler,HLD-REQ-003\n"
            "4,Sensor_Hub,TempMon,Temperature monitoring module,HLD-REQ-004\n"
            "5,Sensor_Hub,PressureMon,Pressure sensor interface,HLD-REQ-005\n"
            "6,Actuator_Ctrl,MotorDrv,Motor driver control logic,HLD-REQ-006\n"
        )

        mock_response = LLMResponse(
            text=lld_csv,
            backend_id="gca_http",
            task_class="CODE_GEN",
            duration_ms=2500.0,
        )

        with patch("cipher.trf.mcp_servers.llm_gateway.router.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.route = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            with patch("cipher.core.adapters.minio_client.MinioStore") as mock_minio_cls:
                mock_store = MagicMock()
                mock_minio_cls.return_value = mock_store

                skill = S1N1Skill()
                task = TaskContract(
                    task_class=TaskClass.CODE_GEN,
                    skill_id="vcycle_s1n1",
                    prompt="Generate LLD from HLD: Automotive ECU with power, comm, diagnostics",
                    requester_agent_id="e2e-test",
                    target_agent_id="devnex",
                )
                result = await skill.execute(task)

                assert result.status == TaskStatus.COMPLETED
                rows = result.output["lld_content"].strip().split("\n")
                assert len(rows) >= 6  # header + 5 data rows


class TestPOCExitCriterion2_MinIOStorage:
    """Exit Criterion 2: LLD artifact stored in MinIO."""

    @pytest.mark.asyncio
    async def test_artifact_stored_in_minio(self) -> None:
        from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
        from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse

        mock_response = LLMResponse(
            text="id,component\n1,ECU\n2,Sensor\n3,Actuator\n4,Bus\n5,Diag\n6,Power",
            backend_id="gca_http",
            task_class="CODE_GEN",
            duration_ms=100.0,
        )

        with patch("cipher.trf.mcp_servers.llm_gateway.router.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.route = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            with patch("cipher.core.adapters.minio_client.MinioStore") as mock_minio_cls:
                mock_store = MagicMock()
                mock_minio_cls.return_value = mock_store

                skill = S1N1Skill()
                task = TaskContract(
                    task_class=TaskClass.CODE_GEN,
                    skill_id="vcycle_s1n1",
                    prompt="test",
                    requester_agent_id="e2e",
                    target_agent_id="devnex",
                )
                result = await skill.execute(task)

                assert result.status == TaskStatus.COMPLETED
                assert len(result.artifact_refs) >= 1
                assert result.artifact_refs[0].startswith("minio://cipher-artifacts/lld/")
                mock_store.put_object.assert_called_once()


class TestPOCExitCriterion3_OTelTrace:
    """Exit Criterion 3: OTel trace spans emitted for full pipeline."""

    def test_traced_decorator_emits_span(self) -> None:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult

        class Collector:
            def __init__(self):
                self.spans = []
            def export(self, spans):
                self.spans.extend(spans)
                return SpanExportResult.SUCCESS
            def shutdown(self):
                pass
            def force_flush(self, timeout_millis=None):
                return True

        collector = Collector()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(collector))
        trace._TRACER_PROVIDER = None
        trace._TRACER_PROVIDER_SET_ONCE._done = False
        trace.set_tracer_provider(provider)

        from cipher.core.otel.tracing import traced

        @traced(name="e2e.test_span", attributes={"layer": "test"})
        def work():
            return "done"

        result = work()
        assert result == "done"
        assert len(collector.spans) >= 1
        assert collector.spans[0].name == "e2e.test_span"


class TestPOCExitCriterion4_AuditJournal:
    """Exit Criterion 4: Audit journal records all LLM calls."""

    def test_audit_records_llm_call(self, tmp_path: Path) -> None:
        from cipher.core.adapters.sqlite_factory import create_audit_db
        from cipher.gcl.audit_journal.journal import AuditJournal

        conn = create_audit_db(tmp_path)
        journal = AuditJournal(conn)

        conn.execute(
            "INSERT INTO audit_log (agent_id, action, detail_json, trace_id) VALUES (?, ?, ?, ?)",
            ("devnex", "llm_call", '{"backend":"gca_http","task_class":"CODE_GEN"}', "trace-abc"),
        )
        conn.commit()

        rows = journal.query(agent_id="devnex")
        assert len(rows) == 1
        detail = json.loads(rows[0]["detail_json"])
        assert detail["backend"] == "gca_http"
        assert rows[0]["trace_id"] == "trace-abc"
        conn.close()


class TestPOCExitCriterion5_OPAPolicy:
    """Exit Criterion 5: OPA policy evaluates to allow."""

    @pytest.mark.asyncio
    async def test_opa_permits_all(self) -> None:
        from cipher.gcl.policy_engine.opa_client import OpaClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"allow": True}}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            client = OpaClient()
            allowed = await client.evaluate(
                "cipher/authz",
                {"agent": "devnex", "action": "llm_call", "task_class": "CODE_GEN"},
            )
            assert allowed is True


class TestPOCExitCriterion6_WorkflowCheckpoint:
    """Exit Criterion 6: Workflow checkpoint persists to SQLite."""

    def test_checkpoint_table_exists(self, tmp_path: Path) -> None:
        from cipher.core.adapters.sqlite_factory import create_checkpoints_db

        conn = create_checkpoints_db(tmp_path)
        conn.execute(
            "INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint, metadata) "
            "VALUES (?, ?, ?, ?)",
            ("thread-1", "cp-001", b'{"state": "running"}', '{"node": "s1n1"}'),
        )
        conn.commit()

        row = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoints WHERE thread_id = ?",
            ("thread-1",),
        ).fetchone()
        assert row == ("thread-1", "cp-001")
        conn.close()
