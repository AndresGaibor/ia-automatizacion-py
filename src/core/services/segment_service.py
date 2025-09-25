"""Service for handling segment operations and mapping."""
import pandas as pd
import os
from typing import Dict, List, Any, Optional, Tuple

from ...shared.utils import data_path
from ...shared.logging import get_logger
from ..errors import DataProcessingError, ValidationError

logger = get_logger()


class SegmentService:
    """Service for handling segment operations, mapping, and file management."""

    def __init__(self):
        self.segments_file = data_path("Segmentos.xlsx")
        self.lists_folder = data_path("listas")

    def get_list_id_from_file(self, list_name: str) -> Optional[int]:
        """Get list ID from file names in the lists folder."""
        if not os.path.exists(self.lists_folder):
            return None

        # Search for files matching the list name
        for filename in os.listdir(self.lists_folder):
            if not filename.endswith('.xlsx'):
                continue

            filename_no_ext = os.path.splitext(filename)[0]

            # Search for pattern: name-ID-[number]
            if filename_no_ext.startswith(list_name + '-ID-'):
                list_id = self._extract_id_from_filename(filename)
                if list_id is not None:
                    logger.info(f"ID found for list '{list_name}': {list_id}")
                    return list_id

            # Also search for files that match exactly with the name (without ID)
            elif filename_no_ext == list_name:
                logger.info(f"File found for list '{list_name}' but without ID")
                return None

        logger.info(f"No file found for list '{list_name}'")
        return None

    def _extract_id_from_filename(self, filename: str) -> Optional[int]:
        """Extract ID from filename with format name-ID-[number].xlsx."""
        try:
            # Extract ID from filename pattern
            filename_no_ext = os.path.splitext(filename)[0]
            parts = filename_no_ext.split('-ID-')
            if len(parts) == 2:
                return int(parts[1])
        except (ValueError, IndexError):
            pass
        return None

    def ensure_filename_with_id(self, list_name: str, list_id: int) -> str:
        """Ensure the local list file uses the format '[List Name]-ID-[List ID].xlsx'."""
        os.makedirs(self.lists_folder, exist_ok=True)

        name_with_id = f"{list_name}-ID-{list_id}.xlsx"
        path_with_id = os.path.join(self.lists_folder, name_with_id)

        name_without_id = f"{list_name}.xlsx"
        path_without_id = os.path.join(self.lists_folder, name_without_id)

        try:
            if os.path.exists(path_with_id):
                # File with ID already exists
                if os.path.exists(path_without_id):
                    logger.warning(
                        f"File without ID also exists for '{list_name}'. Using '{path_with_id}'."
                    )
                return path_with_id

            # If file without ID exists, rename it
            if os.path.exists(path_without_id):
                os.rename(path_without_id, path_with_id)
                logger.info(f"File renamed: '{path_without_id}' → '{path_with_id}'")
                return path_with_id

            # If neither exists, return expected path with ID (will be created later)
            return path_with_id

        except Exception as e:
            logger.error(f"Error ensuring filename with ID for '{list_name}': {e}")
            raise DataProcessingError(
                f"Failed to ensure filename with ID for list '{list_name}'",
                context={"list_name": list_name, "list_id": list_id}
            ) from e

    def update_id_in_segments_file(self, list_name: str, list_id: int) -> bool:
        """Update list ID in the Segments.xlsx file."""
        logger.info(f"Updating ID {list_id} for list '{list_name}' in Segmentos.xlsx")

        try:
            if not os.path.exists(self.segments_file):
                logger.warning(f"Segments file doesn't exist: {self.segments_file}")
                return False

            # Read segments file
            df = pd.read_excel(self.segments_file)

            # Remove "CREACION SEGMENTO" column if it exists
            if 'CREACION SEGMENTO' in df.columns:
                df = df.drop(columns=['CREACION SEGMENTO'])
                logger.info("Column 'CREACION SEGMENTO' removed from Segmentos.xlsx (ID update)")

            # Ensure "ID Lista" column exists
            if 'ID Lista' not in df.columns:
                df.insert(0, 'ID Lista', None)
                logger.info("Column 'ID Lista' added to Segmentos.xlsx file")

            # Update rows matching the list name
            mask = df['NOMBRE LISTA'] == list_name
            updated_rows = mask.sum()

            if updated_rows > 0:
                df.loc[mask, 'ID Lista'] = list_id

                # Save updated file
                df.to_excel(self.segments_file, index=False)
                logger.info(f"Updated ID {list_id} in {updated_rows} rows for list '{list_name}'")
                return True
            else:
                logger.warning(f"No rows found for list '{list_name}' in Segmentos.xlsx")
                return False

        except Exception as e:
            logger.error(f"Error updating ID in Segmentos.xlsx: {e}")
            raise DataProcessingError(
                "Failed to update ID in segments file",
                file_path=str(self.segments_file),
                context={"list_name": list_name, "list_id": list_id}
            ) from e

    def get_id_from_segments_file(self, list_name: str) -> Optional[int]:
        """Get list ID from the Segments.xlsx file."""
        try:
            if not os.path.exists(self.segments_file):
                return None

            df = pd.read_excel(self.segments_file)

            if 'ID Lista' not in df.columns:
                return None

            # Search for first row matching the list name
            mask = df['NOMBRE LISTA'] == list_name
            if mask.any():
                id_value = df.loc[mask, 'ID Lista'].iloc[0]
                if pd.notna(id_value):
                    return int(id_value)

            return None

        except Exception as e:
            logger.error(f"Error reading ID from Segmentos.xlsx: {e}")
            raise DataProcessingError(
                "Failed to read ID from segments file",
                file_path=str(self.segments_file),
                context={"list_name": list_name}
            ) from e

    def get_or_find_list_id(self, list_name: str) -> Optional[int]:
        """Get list ID with priority: Segments.xlsx -> files in /data/listas/ -> None."""
        # 1. Try from Segments.xlsx (if already registered)
        id_from_segments = self.get_id_from_segments_file(list_name)
        if id_from_segments is not None:
            logger.info(f"ID found in Segments.xlsx for '{list_name}': {id_from_segments}")
            return id_from_segments

        # 2. Try from files in /data/listas/ (if file exists with ID)
        id_from_file = self.get_list_id_from_file(list_name)
        if id_from_file is not None:
            logger.info(f"ID found in file for '{list_name}': {id_from_file}")
            # Update Segments.xlsx with found ID
            self.update_id_in_segments_file(list_name, id_from_file)
            return id_from_file

        # 3. Not found
        logger.info(f"No ID found for list '{list_name}'")
        return None

    def validate_segments_file(self) -> Tuple[bool, str, int]:
        """Validate the segments file."""
        if not os.path.exists(self.segments_file):
            return False, "Error: Segmentos.xlsx file does not exist", 0

        try:
            df = pd.read_excel(self.segments_file)
            required_columns = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                return False, f"Error: Missing columns in Segmentos.xlsx: {', '.join(missing_columns)}", 0

            row_count = len(df)
            if row_count == 0:
                return False, "Warning: Segmentos.xlsx file is empty", 0

            return True, f"{row_count} segments defined for processing", row_count

        except Exception as e:
            raise DataProcessingError(
                f"Error reading Segmentos.xlsx: {e}",
                file_path=str(self.segments_file)
            ) from e

    def load_segments_data(self) -> pd.DataFrame:
        """Load and validate segments data from Excel file."""
        try:
            if not os.path.exists(self.segments_file):
                raise ValidationError(f"Segments file not found: {self.segments_file}")

            df = pd.read_excel(self.segments_file)

            # Validate required columns
            required_columns = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                raise ValidationError(
                    f"Missing required columns in segments file: {', '.join(missing_columns)}"
                )

            # Remove unwanted columns if they exist
            if 'CREACION SEGMENTO' in df.columns:
                df = df.drop(columns=['CREACION SEGMENTO'])
                logger.info("Removed 'CREACION SEGMENTO' column from segments data")

            logger.info(f"Loaded {len(df)} segments from file", segments_count=len(df))
            return df

        except Exception as e:
            if isinstance(e, (ValidationError, DataProcessingError)):
                raise
            raise DataProcessingError(
                f"Failed to load segments data: {e}",
                file_path=str(self.segments_file)
            ) from e

    def group_segments_by_list(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Group segments by list name."""
        grouped = {}

        for _, row in df.iterrows():
            list_name = row['NOMBRE LISTA']
            if pd.isna(list_name) or str(list_name).strip() == '':
                continue

            list_name = str(list_name).strip()

            if list_name not in grouped:
                grouped[list_name] = []

            segment_data = {
                'nombre_segmento': str(row.get('NOMBRE SEGMENTO', '')).strip(),
                'id_lista': row.get('ID Lista') if pd.notna(row.get('ID Lista')) else None
            }

            # Add other segment fields dynamically
            for col in df.columns:
                if col not in ['NOMBRE LISTA', 'NOMBRE SEGMENTO', 'ID Lista']:
                    segment_data[col.lower().replace(' ', '_')] = row.get(col)

            grouped[list_name].append(segment_data)

        logger.info(f"Grouped segments into {len(grouped)} lists")
        return grouped