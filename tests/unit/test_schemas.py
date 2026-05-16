"""Unit tests for core Pydantic schemas (T-002). DoD: JSON round-trip tests pass."""

from __future__ import annotations

import json
from uuid import UUID

from cipher.core.schemas import (
    AgentCard,
    ArtifactRelation,
    CloudEvent,
    RelationType,
    SkillDescriptor,
    TaskClass,
    TaskContract,
    TaskResult,
    TaskStatus,
)


class TestTaskContract:
    def test_round_trip(self) -> None:
        tc = TaskContract(
            task_class=TaskClass.CODE_GEN,
            skill_id="vcycle_s1n1",
            prompt="Generate LLD from HLD",
            requester_agent_id="shell",
            target_agent_id="devnex",
        )
        payload = tc.model_dump_json()
        restored = TaskContract.model_validate_json(payload)
        assert restored.task_id == tc.task_id
        assert restored.task_class == TaskClass.CODE_GEN
        assert restored.skill_id == "vcycle_s1n1"

    def test_defaults(self) -> None:
        tc = TaskContract(
            task_class=TaskClass.TRIAGE,
            skill_id="classify",
            prompt="what is this?",
            requester_agent_id="a",
            target_agent_id="b",
        )
        assert isinstance(tc.task_id, UUID)
        assert tc.timeout_s == 300.0
        assert tc.context == {}


class TestTaskResult:
    def test_round_trip(self) -> None:
        tr = TaskResult(
            task_id=TaskContract(
                task_class=TaskClass.PLAN,
                skill_id="plan",
                prompt="p",
                requester_agent_id="a",
                target_agent_id="b",
            ).task_id,
            status=TaskStatus.COMPLETED,
            output={"lld_path": "s3://bucket/lld.csv"},
            artifact_refs=["minio://cipher-artifacts/lld.csv"],
            duration_ms=1234.5,
        )
        payload = tr.model_dump_json()
        restored = TaskResult.model_validate_json(payload)
        assert restored.status == TaskStatus.COMPLETED
        assert restored.artifact_refs == ["minio://cipher-artifacts/lld.csv"]


class TestArtifactRelation:
    def test_round_trip(self) -> None:
        ar = ArtifactRelation(
            source_artifact_id="hld-001",
            target_artifact_id="lld-001",
            relation_type=RelationType.DERIVES_FROM,
            v_cycle_stage="S1N1",
            created_by_agent="devnex",
        )
        payload = ar.model_dump_json()
        restored = ArtifactRelation.model_validate_json(payload)
        assert restored.relation_type == RelationType.DERIVES_FROM
        assert restored.v_cycle_stage == "S1N1"


class TestAgentCard:
    def test_round_trip(self) -> None:
        card = AgentCard(
            agent_id="devnex-001",
            name="DevNex Agent",
            description="Automotive V-cycle agent",
            url="http://localhost:8100",
            skills=[
                SkillDescriptor(
                    skill_id="vcycle_s1n1",
                    name="S1N1 LLD Generation",
                    description="Generates Low-Level Design from HLD",
                    supported_task_classes=["CODE_GEN"],
                    v_cycle_stages=["S1N1"],
                )
            ],
        )
        payload = card.model_dump_json()
        restored = AgentCard.model_validate_json(payload)
        assert restored.agent_id == "devnex-001"
        assert len(restored.skills) == 1
        assert restored.skills[0].skill_id == "vcycle_s1n1"

    def test_defaults(self) -> None:
        card = AgentCard(
            agent_id="x", name="X", description="d", url="http://localhost:9000"
        )
        assert card.supported_protocols == ["a2a/v1"]
        assert card.version == "0.1.0"


class TestCloudEvent:
    def test_round_trip(self) -> None:
        evt = CloudEvent(
            source="cipher.are.a2a_server",
            type="cipher.task.completed",
            subject="task-123",
            data={"task_id": "abc", "status": "COMPLETED"},
        )
        payload = evt.model_dump_json()
        restored = CloudEvent.model_validate_json(payload)
        assert restored.type == "cipher.task.completed"
        assert restored.specversion == "1.0"
        assert restored.data["task_id"] == "abc"

    def test_json_stdlib_compat(self) -> None:
        evt = CloudEvent(
            source="test", type="test.event", data={"key": "value"}
        )
        raw = json.loads(evt.model_dump_json())
        assert raw["specversion"] == "1.0"
        assert raw["datacontenttype"] == "application/json"
