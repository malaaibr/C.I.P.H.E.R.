"""Tests for the IssueReport schema."""

from cipher.core.schemas.issue_report import (
    IssueReport,
    ValidationVerdict,
    ViolationType,
    WellFormednessViolation,
)


class TestWellFormednessViolation:
    def test_create_violation(self):
        v = WellFormednessViolation(
            step_index=3,
            violation_type=ViolationType.UNRESOLVED,
            message="URI not found",
            expected="mkf://Dio.c",
            actual="mkf://NonExistent.c",
            citation_uri="mkf://NonExistent.c",
        )
        assert v.step_index == 3
        assert v.violation_type == ViolationType.UNRESOLVED


class TestIssueReport:
    def test_pass_report(self):
        r = IssueReport(
            crc_target_artifact="LLD-Dio:v1",
            verdict=ValidationVerdict.PASS,
        )
        assert r.is_pass
        assert r.violation_count == 0

    def test_fail_report(self):
        r = IssueReport(
            crc_target_artifact="LLD-Dio:v1",
            verdict=ValidationVerdict.FAIL,
            violations=[
                WellFormednessViolation(
                    step_index=1,
                    violation_type=ViolationType.UNCITED,
                    message="No citations",
                )
            ],
        )
        assert not r.is_pass
        assert r.violation_count == 1

    def test_serialization_roundtrip(self):
        r = IssueReport(
            crc_target_artifact="LLD-Test:v1",
            verdict=ValidationVerdict.FAIL,
            violations=[
                WellFormednessViolation(
                    step_index=2,
                    violation_type=ViolationType.FIELD_MISMATCH,
                    message="Frequency mismatch",
                    expected="1.5 Hz",
                    actual="3.0 Hz",
                )
            ],
            revision_number=2,
        )
        json_str = r.model_dump_json()
        restored = IssueReport.model_validate_json(json_str)
        assert restored.violation_count == 1
        assert restored.violations[0].expected == "1.5 Hz"
