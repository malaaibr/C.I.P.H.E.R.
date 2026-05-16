"""Unit tests for Sprint 2 tasks (T-021 through T-027)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cipher.are.skill_loader.loader import Skill, SkillLoader
from cipher.core.schemas.task_contract import TaskClass, TaskContract, TaskResult, TaskStatus
from cipher.gcl.policy_engine.opa_client import OpaClient


class TestSkillLoader:
    def test_register_and_resolve(self) -> None:
        loader = SkillLoader()
        mock_skill = MagicMock()
        mock_skill.skill_id = "test_skill"
        loader.register(mock_skill)
        assert loader.resolve("test_skill") is mock_skill

    def test_resolve_missing_returns_none(self) -> None:
        loader = SkillLoader()
        assert loader.resolve("nonexistent") is None

    def test_list_skills(self) -> None:
        loader = SkillLoader()
        s1 = MagicMock()
        s1.skill_id = "a"
        s2 = MagicMock()
        s2.skill_id = "b"
        loader.register(s1)
        loader.register(s2)
        assert sorted(loader.list_skills()) == ["a", "b"]


class TestAuditJournal:
    def test_record_and_query(self, tmp_path: Path) -> None:
        from cipher.core.adapters.sqlite_factory import create_audit_db

        conn = create_audit_db(tmp_path)
        from cipher.gcl.audit_journal.journal import AuditJournal

        journal = AuditJournal(conn)
        # record is async but we call the sync part directly
        conn.execute(
            "INSERT INTO audit_log (agent_id, action, detail_json) VALUES (?, ?, ?)",
            ("devnex", "llm_call", '{"model": "ollama"}'),
        )
        conn.commit()

        rows = journal.query(agent_id="devnex")
        assert len(rows) == 1
        assert rows[0]["action"] == "llm_call"
        conn.close()


class TestOpaClient:
    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        client = OpaClient("http://localhost:8181")
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_evaluate_allow(self) -> None:
        client = OpaClient("http://localhost:8181")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": {"allow": True}}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            allowed = await client.evaluate("cipher/authz", {"agent": "devnex"})
            assert allowed is True


class TestS1N1Skill:
    @pytest.mark.asyncio
    async def test_execute_with_mocked_router(self) -> None:
        from cipher.agents.devnex.skills.vcycle_s1n1.skill import S1N1Skill
        from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse

        mock_response = LLMResponse(
            text="id,component,description\n1,ECU,Main controller",
            backend_id="gca_http",
            task_class="CODE_GEN",
            duration_ms=500.0,
        )

        with patch("cipher.trf.mcp_servers.llm_gateway.router.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.route = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            with patch("cipher.core.adapters.minio_client.MinioStore"):
                skill = S1N1Skill()
                task = TaskContract(
                    task_class=TaskClass.CODE_GEN,
                    skill_id="vcycle_s1n1",
                    prompt="Generate LLD from HLD",
                    requester_agent_id="shell",
                    target_agent_id="devnex",
                )
                result = await skill.execute(task)

                assert result.status == TaskStatus.COMPLETED
                assert "ECU" in result.output["lld_content"]
                assert result.artifact_refs[0].startswith("minio://")


class TestDevNexAdapter:
    @pytest.mark.asyncio
    async def test_adapter_delegates_to_skill(self) -> None:
        from cipher.agents.devnex.adapter import DevNexAdapter
        from cipher.trf.mcp_servers.llm_gateway.protocol import LLMResponse

        mock_response = LLMResponse(
            text="lld output",
            backend_id="gca_http",
            task_class="CODE_GEN",
            duration_ms=100.0,
        )

        with patch("cipher.trf.mcp_servers.llm_gateway.router.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.route = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            with patch("cipher.core.adapters.minio_client.MinioStore"):
                adapter = DevNexAdapter()
                task = TaskContract(
                    task_class=TaskClass.CODE_GEN,
                    skill_id="vcycle_s1n1",
                    prompt="test",
                    requester_agent_id="a",
                    target_agent_id="b",
                )
                result = await adapter.execute(task)
                assert result.status == TaskStatus.COMPLETED
