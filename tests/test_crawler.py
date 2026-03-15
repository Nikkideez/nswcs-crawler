"""Unit tests for the crawler module."""

import pytest

from src.crawler import OrderInfo, _classify_order, _extract_acn, _extract_address


class TestClassifyOrder:
    def test_stop_work(self):
        assert _classify_order("Stop Work Order for Acme Pty Ltd") == "Stop work order"

    def test_rectification(self):
        title = "Building Work Rectification Order for Foo Corp"
        assert _classify_order(title) == "Building work rectification order"

    def test_prohibition(self):
        assert _classify_order("Prohibition Order – Bar Ltd") == "Prohibition order"

    def test_unknown(self):
        assert _classify_order("Something else entirely") == "Unknown"

    def test_case_insensitive(self):
        assert _classify_order("STOP WORK ORDER FOR XYZ") == "Stop work order"


class TestExtractACN:
    def test_standard_acn(self):
        assert _extract_acn("Company ACN: 002 026 191 is hereby ordered") == "002 026 191"

    def test_acn_no_colon(self):
        assert _extract_acn("ACN 123 456 789") == "123 456 789"

    def test_no_acn(self):
        assert _extract_acn("No company number here") == ""


class TestExtractAddress:
    def test_from_description(self):
        desc = "9 Young Street, Neutral Bay NSW 2089"
        assert "9 Young Street" in _extract_address(desc, "")

    def test_from_page_text(self):
        text = "The building at 123 Example Road, Sydney NSW 2000 requires work"
        result = _extract_address("", text)
        assert "123 Example Road" in result

    def test_empty(self):
        assert _extract_address("", "") == ""


class TestOrderInfo:
    def test_defaults(self):
        info = OrderInfo()
        assert info.title == ""
        assert info.source_url == ""

    def test_creation(self):
        info = OrderInfo(
            title="Test Order",
            order_type="Stop work order",
            company_name="Test Co",
            source_url="https://example.com/order",
        )
        assert info.company_name == "Test Co"
        assert info.order_type == "Stop work order"
