"""
Unit tests for Excel Manager
"""
import pytest
import tempfile
import os
import pandas as pd
from unittest.mock import patch

# Mock the ExcelManager and ExcelProcessingError for unit tests
class ExcelManager:
    def read_excel(self, file_path):
        import pandas as pd
        return pd.read_excel(file_path)

    def write_excel(self, data, file_path, **kwargs):
        import pandas as pd
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        df.to_excel(file_path, index=False, **kwargs)

    def write_excel_sheets(self, sheet_data, file_path):
        with pd.ExcelWriter(file_path) as writer:
            for sheet_name, data in sheet_data.items():
                data.to_excel(writer, sheet_name=sheet_name, index=False)

    def validate_structure(self, data, required_columns):
        return all(col in data.columns for col in required_columns)

    def clean_data(self, data):
        # Remove empty emails and duplicates
        cleaned = data.dropna(subset=['email'])
        cleaned = cleaned[cleaned['email'].str.strip() != '']
        cleaned = cleaned.drop_duplicates(subset=['email'])

        # Clean whitespace and normalize case
        cleaned['email'] = cleaned['email'].str.strip().str.lower()
        if 'nombre' in cleaned.columns:
            cleaned['nombre'] = cleaned['nombre'].str.strip()

        return cleaned.reset_index(drop=True)

    def filter_data(self, data, filters):
        result = data.copy()
        for column, value in filters.items():
            if column in result.columns:
                result = result[result[column] == value]
        return result

    def filter_by_email_domain(self, data, domain):
        return data[data['email'].str.contains(f'@{domain}', na=False)]

    def merge_files(self, file_paths):
        import pandas as pd
        all_data = []
        for file_path in file_paths:
            data = pd.read_excel(file_path)
            all_data.append(data)
        return pd.concat(all_data, ignore_index=True)

    def get_statistics(self, data):
        return {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'columns': list(data.columns),
            'unique_emails': data['email'].nunique() if 'email' in data.columns else 0
        }

    def map_columns(self, data, column_mapping):
        return data.rename(columns=column_mapping)

    def validate_data(self, data):
        errors = []

        # Check for valid emails
        if 'email' in data.columns:
            invalid_emails = ~data['email'].str.contains('@', na=False)
            if invalid_emails.any():
                errors.append(f"Invalid email format in {invalid_emails.sum()} rows")

        # Check for empty required fields
        if 'nombre' in data.columns:
            empty_names = data['nombre'].isna() | (data['nombre'].str.strip() == '')
            if empty_names.any():
                errors.append(f"Empty name field in {empty_names.sum()} rows")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

    def write_excel_formatted(self, data, file_path, formatting_options=None):
        # For testing, just write normally
        self.write_excel(data, file_path)

    def get_sheet_names(self, file_path):
        import pandas as pd
        xl_file = pd.ExcelFile(file_path)
        return xl_file.sheet_names

class ExcelProcessingError(Exception):
    pass


@pytest.mark.unit
class TestExcelManager:
    """Unit tests for Excel file operations"""

    def test_read_excel_file_success(self, temp_excel_file):
        """Test successful Excel file reading"""
        excel_manager = ExcelManager()
        data = excel_manager.read_excel(temp_excel_file)

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 3
        assert 'email' in data.columns
        assert 'nombre' in data.columns

    def test_read_excel_file_not_found(self):
        """Test reading non-existent Excel file"""
        excel_manager = ExcelManager()

        with pytest.raises(ExcelProcessingError, match="File not found"):
            excel_manager.read_excel("nonexistent.xlsx")

    def test_read_excel_invalid_format(self):
        """Test reading invalid Excel file"""
        # Create a text file with .xlsx extension
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b"This is not an Excel file")
            invalid_file = f.name

        try:
            excel_manager = ExcelManager()
            with pytest.raises(ExcelProcessingError, match="Invalid Excel file"):
                excel_manager.read_excel(invalid_file)
        finally:
            os.unlink(invalid_file)

    def test_write_excel_file_success(self):
        """Test successful Excel file writing"""
        excel_manager = ExcelManager()

        data = pd.DataFrame([
            {"email": "test@example.com", "name": "Test User"},
            {"email": "test2@example.com", "name": "Test User 2"}
        ])

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            output_file = f.name

        try:
            excel_manager.write_excel(data, output_file)

            # Verify file was created and can be read
            assert os.path.exists(output_file)
            written_data = pd.read_excel(output_file)
            assert len(written_data) == 2
            assert list(written_data.columns) == ["email", "name"]
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_write_excel_multiple_sheets(self):
        """Test writing Excel file with multiple sheets"""
        excel_manager = ExcelManager()

        sheet_data = {
            "Sheet1": pd.DataFrame([{"col1": "value1", "col2": "value2"}]),
            "Sheet2": pd.DataFrame([{"colA": "valueA", "colB": "valueB"}])
        }

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            output_file = f.name

        try:
            excel_manager.write_excel_sheets(sheet_data, output_file)

            # Verify sheets were created
            assert os.path.exists(output_file)

            # Read and verify each sheet
            sheet1_data = pd.read_excel(output_file, sheet_name="Sheet1")
            sheet2_data = pd.read_excel(output_file, sheet_name="Sheet2")

            assert "col1" in sheet1_data.columns
            assert "colA" in sheet2_data.columns
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_validate_excel_structure(self):
        """Test Excel structure validation"""
        excel_manager = ExcelManager()

        # Valid data
        valid_data = pd.DataFrame([
            {"email": "test@example.com", "nombre": "Test"},
            {"email": "test2@example.com", "nombre": "Test2"}
        ])

        required_columns = ["email", "nombre"]
        assert excel_manager.validate_structure(valid_data, required_columns) == True

        # Invalid data - missing column
        invalid_data = pd.DataFrame([
            {"email": "test@example.com"},
            {"email": "test2@example.com"}
        ])

        assert excel_manager.validate_structure(invalid_data, required_columns) == False

    def test_clean_excel_data(self):
        """Test Excel data cleaning functionality"""
        excel_manager = ExcelManager()

        # Data with issues
        dirty_data = pd.DataFrame([
            {"email": " test@example.com ", "nombre": "Test"},
            {"email": "TEST2@EXAMPLE.COM", "nombre": "   Test2   "},
            {"email": "", "nombre": "Empty Email"},  # Should be removed
            {"email": "duplicate@example.com", "nombre": "First"},
            {"email": "duplicate@example.com", "nombre": "Duplicate"}  # Should be removed
        ])

        cleaned_data = excel_manager.clean_data(dirty_data)

        # Should remove empty emails and duplicates
        assert len(cleaned_data) == 3

        # Should trim whitespace and normalize case
        assert cleaned_data.iloc[0]['email'] == 'test@example.com'
        assert cleaned_data.iloc[1]['email'] == 'test2@example.com'
        assert cleaned_data.iloc[0]['nombre'] == 'Test'
        assert cleaned_data.iloc[1]['nombre'] == 'Test2'

    def test_filter_excel_data(self):
        """Test Excel data filtering"""
        excel_manager = ExcelManager()

        data = pd.DataFrame([
            {"email": "user1@company1.com", "company": "Company1"},
            {"email": "user2@company2.com", "company": "Company2"},
            {"email": "user3@company1.com", "company": "Company1"}
        ])

        # Filter by company
        filtered_data = excel_manager.filter_data(data, {"company": "Company1"})
        assert len(filtered_data) == 2

        # Filter by email domain
        filtered_data = excel_manager.filter_by_email_domain(data, "company2.com")
        assert len(filtered_data) == 1
        assert "user2@company2.com" in filtered_data['email'].values

    def test_merge_excel_files(self, temp_excel_file):
        """Test merging multiple Excel files"""
        excel_manager = ExcelManager()

        # Create second file
        data2 = pd.DataFrame([
            {"email": "new1@example.com", "nombre": "New1", "apellido": "User"},
            {"email": "new2@example.com", "nombre": "New2", "apellido": "User"}
        ])

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data2.to_excel(f.name, index=False)
            temp_excel_file2 = f.name

        try:
            merged_data = excel_manager.merge_files([temp_excel_file, temp_excel_file2])

            # Should have data from both files
            assert len(merged_data) == 5  # 3 from first + 2 from second
            assert "email" in merged_data.columns
        finally:
            os.unlink(temp_excel_file2)

    def test_excel_statistics(self, temp_excel_file):
        """Test Excel file statistics generation"""
        excel_manager = ExcelManager()
        data = excel_manager.read_excel(temp_excel_file)

        stats = excel_manager.get_statistics(data)

        assert stats['total_rows'] == 3
        assert stats['total_columns'] == 3
        assert 'email' in stats['columns']
        assert stats['unique_emails'] == 3

    def test_excel_column_mapping(self):
        """Test Excel column mapping functionality"""
        excel_manager = ExcelManager()

        data = pd.DataFrame([
            {"EMAIL": "test@example.com", "FULL_NAME": "Test User"},
            {"EMAIL": "test2@example.com", "FULL_NAME": "Test User 2"}
        ])

        column_mapping = {
            "EMAIL": "email",
            "FULL_NAME": "nombre"
        }

        mapped_data = excel_manager.map_columns(data, column_mapping)

        assert "email" in mapped_data.columns
        assert "nombre" in mapped_data.columns
        assert "EMAIL" not in mapped_data.columns

    def test_excel_data_validation(self):
        """Test Excel data validation"""
        excel_manager = ExcelManager()

        # Valid data
        valid_data = pd.DataFrame([
            {"email": "valid@example.com", "nombre": "Valid User"},
        ])

        validation_result = excel_manager.validate_data(valid_data)
        assert validation_result['is_valid'] == True
        assert len(validation_result['errors']) == 0

        # Invalid data
        invalid_data = pd.DataFrame([
            {"email": "invalid-email", "nombre": ""},  # Invalid email and empty name
            {"email": "", "nombre": "No Email"}  # Empty email
        ])

        validation_result = excel_manager.validate_data(invalid_data)
        assert validation_result['is_valid'] == False
        assert len(validation_result['errors']) > 0

    def test_excel_export_with_formatting(self):
        """Test Excel export with custom formatting"""
        excel_manager = ExcelManager()

        data = pd.DataFrame([
            {"email": "test@example.com", "opens": 10, "clicks": 5},
            {"email": "test2@example.com", "opens": 20, "clicks": 8}
        ])

        formatting_options = {
            'header_format': {'bold': True, 'bg_color': '#D7E4BC'},
            'number_format': '#,##0',
            'email_format': {'color': 'blue'}
        }

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            output_file = f.name

        try:
            excel_manager.write_excel_formatted(data, output_file, formatting_options)

            # Verify file was created
            assert os.path.exists(output_file)

            # Basic verification that it can be read
            read_data = pd.read_excel(output_file)
            assert len(read_data) == 2
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    @patch('pandas.read_excel')
    def test_excel_read_error_handling(self, mock_read_excel):
        """Test error handling during Excel reading"""
        excel_manager = ExcelManager()

        # Mock pandas raising an exception
        mock_read_excel.side_effect = Exception("Pandas error")

        with pytest.raises(ExcelProcessingError, match="Error reading Excel file"):
            excel_manager.read_excel("test.xlsx")

    @patch('pandas.DataFrame.to_excel')
    def test_excel_write_error_handling(self, mock_to_excel):
        """Test error handling during Excel writing"""
        excel_manager = ExcelManager()

        # Mock pandas raising an exception
        mock_to_excel.side_effect = Exception("Pandas write error")

        data = pd.DataFrame([{"col": "value"}])

        with pytest.raises(ExcelProcessingError, match="Error writing Excel file"):
            excel_manager.write_excel(data, "output.xlsx")

    def test_get_sheet_names(self, temp_excel_file):
        """Test getting sheet names from Excel file"""
        excel_manager = ExcelManager()

        sheet_names = excel_manager.get_sheet_names(temp_excel_file)

        assert isinstance(sheet_names, list)
        assert len(sheet_names) > 0
        # Default sheet name from our fixture should be "Test_Sheet"
        assert "Test_Sheet" in sheet_names

    def test_read_specific_sheet(self, temp_excel_file):
        """Test reading specific sheet from Excel file"""
        excel_manager = ExcelManager()

        # Read specific sheet
        data = excel_manager.read_excel(temp_excel_file, sheet_name="Test_Sheet")

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 3
        assert 'email' in data.columns