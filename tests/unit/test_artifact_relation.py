"""Tests for enhanced ArtifactRelation schema."""

from datetime import UTC, datetime

from cipher.core.schemas.artifact_relation import ArtifactRelation, RelationType


class TestRelationTypeEnhancements:
    def test_new_relation_types_exist(self):
        assert RelationType.GENERATED_BY == "GENERATED_BY"
        assert RelationType.APPROVED_BY == "APPROVED_BY"
        assert RelationType.VIOLATES == "VIOLATES"
        assert RelationType.CONFORMS_TO == "CONFORMS_TO"

    def test_original_types_preserved(self):
        assert RelationType.DERIVES_FROM == "DERIVES_FROM"
        assert RelationType.IMPLEMENTS == "IMPLEMENTS"
        assert RelationType.TESTS == "TESTS"


class TestArtifactRelationTemporalFields:
    def test_defaults(self):
        r = ArtifactRelation(
            source_artifact_id="LLD-Dio:v1",
            target_artifact_id="DevNex-AGT-001",
            relation_type=RelationType.GENERATED_BY,
        )
        assert r.confidence == 1.0
        assert r.valid_from is None
        assert r.valid_to is None

    def test_temporal_edges(self):
        now = datetime.now(UTC)
        r = ArtifactRelation(
            source_artifact_id="LLD-Dio:v2",
            target_artifact_id="LLD-Dio:v1",
            relation_type=RelationType.SUPERSEDES,
            valid_from=now,
            confidence=0.95,
        )
        assert r.valid_from == now
        assert r.confidence == 0.95
