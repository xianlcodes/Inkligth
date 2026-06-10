"""Export schemas and data model tests (unittest)."""

import unittest

# Note: These tests require pydantic which is part of the InkLight backend
# dependencies. They validate the export schemas defined in app.export.schemas.


class TestExportModels(unittest.TestCase):
    """Export data model tests."""

    def test_export_record_default_expiry(self):
        from app.export.models import ExportRecord
        expiry = ExportRecord.default_expiry()
        self.assertIsNotNone(expiry)


class TestExportSchemasImports(unittest.TestCase):
    """Verify that all schemas can be imported."""

    def test_import_schemas(self):
        """Test that all export schema classes can be imported."""
        from app.export.schemas import (
            ExportFormat,
            ExportSource,
            WordExportRequest,
            WordExportOptions,
            LatexExportRequest,
            LatexExportOptions,
            PdfExportRequest,
            ExportResponse,
            ExportHistoryItem,
            ExportHistoryResponse,
            FileInfo,
        )
        self.assertTrue(hasattr(WordExportRequest, 'source_type'))
        self.assertTrue(hasattr(LatexExportRequest, 'options'))
        self.assertTrue(hasattr(ExportResponse, 'export_id'))
        self.assertTrue(hasattr(ExportHistoryResponse, 'items'))


if __name__ == "__main__":
    unittest.main()
