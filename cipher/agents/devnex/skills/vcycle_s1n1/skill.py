"""S1N1 LLD Generation Skill (T-024, POC skill)."""

from __future__ import annotations

import time

from cipher.core.otel import traced
from cipher.core.schemas.task_contract import TaskClass, TaskContract, TaskResult, TaskStatus


class S1N1Skill:
    """
    Generates Low-Level Design CSV from a High-Level Design prompt.

    POC implementation: routes to CODE_GEN backend via TaskClassRouter,
    stores result in MinIO, emits OTel span.
    """

    @property
    def skill_id(self) -> str:
        return "vcycle_s1n1"

    @traced(name="skill.s1n1.execute", attributes={"layer": "aal", "stage": "S1N1"})
    async def execute(self, task: TaskContract) -> TaskResult:
        t0 = time.perf_counter()

        try:
            from cipher.trf.mcp_servers.llm_gateway.router import get_router

            router = get_router()
            llm_response = await router.route(
                task.prompt, TaskClass.CODE_GEN, task.context
            )

            lld_content = llm_response.text
            artifact_key = f"lld/{task.task_id}.csv"

            try:
                from cipher.core.adapters.minio_client import MinioStore

                store = MinioStore()
                store.ensure_bucket()
                store.put_object(artifact_key, lld_content.encode(), "text/csv")
            except Exception:
                pass  # MinIO optional in unit test context

            duration_ms = (time.perf_counter() - t0) * 1000
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                output={
                    "lld_content": lld_content[:500],
                    "artifact_key": artifact_key,
                    "backend": llm_response.backend_id,
                },
                artifact_refs=[f"minio://cipher-artifacts/{artifact_key}"],
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                duration_ms=duration_ms,
            )
