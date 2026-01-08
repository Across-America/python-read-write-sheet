"""
Smartsheet Service - Handles all Smartsheet API interactions
"""

import smartsheet
from config import SMARTSHEET_ACCESS_TOKEN


class SmartsheetService:
    """Service for interacting with Smartsheet API"""

    def __init__(self, sheet_id=None, sheet_name=None, workspace_name=None,
                 workspace_id=None, folder_id=None, cache_enabled=True):
        """
        Initialize SmartsheetService with flexible sheet location options

        Args:
            sheet_id (int, optional): Direct sheet ID (traditional method)
            sheet_name (str, optional): Name of the sheet to find
            workspace_name (str, optional): Workspace name (used with sheet_name)
            workspace_id (int, optional): Workspace ID (used with sheet_name)
            folder_id (int, optional): Folder ID (used with sheet_name)
            cache_enabled (bool): Whether to cache sheet_id after finding (default: True)

        Usage Examples:
            # Method 1: Direct sheet ID (traditional, backward compatible)
            service = SmartsheetService(sheet_id=123456789)

            # Method 2: By sheet name (searches all accessible sheets)
            service = SmartsheetService(sheet_name="Cancellation Dev Sheet")

            # Method 3: By workspace name + sheet name
            service = SmartsheetService(workspace_name="Insurance", sheet_name="Cancellation Dev")

            # Method 4: By workspace ID + sheet name
            service = SmartsheetService(workspace_id=987654321, sheet_name="Cancellation Dev")

            # Method 5: By folder ID + sheet name
            service = SmartsheetService(folder_id=456789123, sheet_name="Cancellation Dev")
        """
        self.smart = smartsheet.Smartsheet(access_token=SMARTSHEET_ACCESS_TOKEN)
        self.smart.errors_as_exceptions(True)
        self.cache_enabled = cache_enabled
        self._cached_sheet_id = None

        # Validate parameters
        if not any([sheet_id, sheet_name]):
            raise ValueError("Must provide either sheet_id or sheet_name")

        # Method 1: Direct sheet ID (backward compatible)
        if sheet_id:
            self.sheet_id = sheet_id
            self._cached_sheet_id = sheet_id
            return

        # Method 2: Find by sheet name with various location options
        if sheet_name:
            found_sheet_id = None

            # Option A: Search in specific workspace (by name)
            if workspace_name:
                print(f"🔍 Looking for sheet '{sheet_name}' in workspace '{workspace_name}'...")
                found_sheet_id = self._find_sheet_in_workspace_by_name(workspace_name, sheet_name)

            # Option B: Search in specific workspace (by ID)
            elif workspace_id:
                print(f"🔍 Looking for sheet '{sheet_name}' in workspace ID {workspace_id}...")
                found_sheet_id = self._find_sheet_in_workspace_by_id(workspace_id, sheet_name)

            # Option C: Search in specific folder
            elif folder_id:
                print(f"🔍 Looking for sheet '{sheet_name}' in folder ID {folder_id}...")
                found_sheet_id = self._find_sheet_in_folder(folder_id, sheet_name)

            # Option D: Search all accessible sheets
            else:
                print(f"🔍 Searching for sheet '{sheet_name}' in all accessible locations...")
                found_sheet_id = self._find_sheet_by_name(sheet_name)

            if found_sheet_id:
                self.sheet_id = found_sheet_id
                if self.cache_enabled:
                    self._cached_sheet_id = found_sheet_id
                print(f"✅ Found sheet: '{sheet_name}' (ID: {found_sheet_id})")
            else:
                raise ValueError(
                    f"❌ Sheet '{sheet_name}' not found. "
                    f"Please check the sheet name and your access permissions."
                )
    

    def _get_column_mapping(self, sheet):
        """
        Get column ID mapping for ALL columns in the sheet

        Returns:
            dict: Mapping of normalized field names to column IDs
                  e.g., {'client_id': 123, 'phone_number': 456, ...}
        """
        # Use the unified _build_column_map and return name->id mapping
        _, name_map = self._build_column_map(sheet)

        # Convert to simple field_name -> column_id mapping
        columns = {field_name: info['id'] for field_name, info in name_map.items()}
        return columns
    

    # ========================================
    # Private Helper Methods for Sheet Lookup
    # ========================================

    def _find_sheet_by_name(self, sheet_name):
        """
        Find a sheet by name across all accessible sheets

        Args:
            sheet_name (str): Name of the sheet to find

        Returns:
            int or None: Sheet ID if found, None otherwise
        """
        try:
            # List all sheets accessible to the user
            response = self.smart.Sheets.list_sheets(include_all=True)
            sheets = response.data

            # Search for exact match (case-insensitive)
            for sheet in sheets:
                if sheet.name.lower() == sheet_name.lower():
                    return sheet.id

            # If no exact match, try partial match
            for sheet in sheets:
                if sheet_name.lower() in sheet.name.lower():
                    print(f"   ℹ️  Found partial match: '{sheet.name}'")
                    return sheet.id

            return None

        except Exception as e:
            print(f"❌ Error searching for sheet: {e}")
            return None

    def _find_sheet_in_workspace_by_name(self, workspace_name, sheet_name):
        """
        Find a sheet in a specific workspace by workspace name

        Args:
            workspace_name (str): Name of the workspace
            sheet_name (str): Name of the sheet to find

        Returns:
            int or None: Sheet ID if found, None otherwise
        """
        try:
            # First, find the workspace by name
            workspace_id = self._find_workspace_by_name(workspace_name)

            if not workspace_id:
                print(f"❌ Workspace '{workspace_name}' not found")
                return None

            # Then search in that workspace
            return self._find_sheet_in_workspace_by_id(workspace_id, sheet_name)

        except Exception as e:
            print(f"❌ Error searching workspace: {e}")
            return None

    def _find_sheet_in_workspace_by_id(self, workspace_id, sheet_name):
        """
        Find a sheet in a specific workspace by workspace ID

        Args:
            workspace_id (int): Workspace ID
            sheet_name (str): Name of the sheet to find

        Returns:
            int or None: Sheet ID if found, None otherwise
        """
        try:
            # Get workspace contents (includes all sheets, folders, reports)
            workspace = self.smart.Workspaces.get_workspace(workspace_id, load_all=True)

            # Search in sheets directly in workspace
            if hasattr(workspace, 'sheets') and workspace.sheets:
                for sheet in workspace.sheets:
                    if sheet.name.lower() == sheet_name.lower():
                        return sheet.id

            # Search in folders within workspace
            if hasattr(workspace, 'folders') and workspace.folders:
                for folder in workspace.folders:
                    sheet_id = self._search_folder_recursively(folder, sheet_name)
                    if sheet_id:
                        return sheet_id

            return None

        except Exception as e:
            print(f"❌ Error accessing workspace {workspace_id}: {e}")
            return None

    def _find_sheet_in_folder(self, folder_id, sheet_name):
        """
        Find a sheet in a specific folder

        Args:
            folder_id (int): Folder ID
            sheet_name (str): Name of the sheet to find

        Returns:
            int or None: Sheet ID if found, None otherwise
        """
        try:
            # Get folder contents
            folder = self.smart.Folders.get_folder(folder_id)

            # Search in this folder
            if hasattr(folder, 'sheets') and folder.sheets:
                for sheet in folder.sheets:
                    if sheet.name.lower() == sheet_name.lower():
                        return sheet.id

            # Search in subfolders recursively
            if hasattr(folder, 'folders') and folder.folders:
                for subfolder in folder.folders:
                    sheet_id = self._search_folder_recursively(subfolder, sheet_name)
                    if sheet_id:
                        return sheet_id

            return None

        except Exception as e:
            print(f"❌ Error accessing folder {folder_id}: {e}")
            return None

    def _find_workspace_by_name(self, workspace_name):
        """
        Find a workspace by name

        Args:
            workspace_name (str): Name of the workspace

        Returns:
            int or None: Workspace ID if found, None otherwise
        """
        try:
            # List all workspaces
            response = self.smart.Workspaces.list_workspaces(include_all=True)
            workspaces = response.data

            # Search for exact match (case-insensitive)
            for workspace in workspaces:
                if workspace.name.lower() == workspace_name.lower():
                    return workspace.id

            # If no exact match, try partial match
            for workspace in workspaces:
                if workspace_name.lower() in workspace.name.lower():
                    print(f"   ℹ️  Found partial workspace match: '{workspace.name}'")
                    return workspace.id

            return None

        except Exception as e:
            print(f"❌ Error searching for workspace: {e}")
            return None

    def _search_folder_recursively(self, folder, sheet_name):
        """
        Recursively search for a sheet in a folder and its subfolders

        Args:
            folder: Folder object
            sheet_name (str): Name of the sheet to find

        Returns:
            int or None: Sheet ID if found, None otherwise
        """
        try:
            # Get full folder details
            folder_details = self.smart.Folders.get_folder(folder.id)

            # Search in sheets directly in this folder
            if hasattr(folder_details, 'sheets') and folder_details.sheets:
                for sheet in folder_details.sheets:
                    if sheet.name.lower() == sheet_name.lower():
                        return sheet.id

            # Search in subfolders
            if hasattr(folder_details, 'folders') and folder_details.folders:
                for subfolder in folder_details.folders:
                    sheet_id = self._search_folder_recursively(subfolder, sheet_name)
                    if sheet_id:
                        return sheet_id

            return None

        except Exception as e:
            print(f"❌ Error searching folder {folder.id}: {e}")
            return None

    # ========================================
    # End of Private Helper Methods
    # ========================================

    def get_all_customers_with_stages(self):
        """
        Get all customers with their stage information (for multi-stage calling)

        Returns:
            list: List of customer records with all fields including stages
        """
        try:
            print("🔍 Loading all customers with stage information...")
            sheet = self.smart.Sheets.get_sheet(self.sheet_id)

            # Build column mapping once (use id_map for row extraction)
            id_map, name_map = self._build_column_map(sheet)

            customers = []

            # Process all rows using pre-built column map
            # Note: sheet.rows order may vary, so we'll sort by row_number later if needed
            for row in sheet.rows:
                customer = self._extract_all_row_data(row, id_map)
                if customer:
                    customers.append(customer)

            print(f"✅ Loaded {len(customers)} customer records")
            
            # Sort by row_number to ensure consistent order (ascending)
            def get_row_number(customer):
                row_num = customer.get('row_number', 0)
                if row_num is None:
                    return 0
                try:
                    return int(row_num)
                except (ValueError, TypeError):
                    return 0
            
            customers.sort(key=get_row_number)
            
            return customers

        except Exception as e:
            error_msg = str(e)
            # Check if it's a 404 error
            if "404" in error_msg or "Not Found" in error_msg or "1006" in error_msg:
                print(f"❌ Error loading customers: Smartsheet API returned 404 Not Found")
                print(f"   This usually means:")
                print(f"   - Sheet ID {self.sheet_id} does not exist or is inaccessible")
                print(f"   - SMARTSHEET_ACCESS_TOKEN does not have permission to access this sheet")
                print(f"   - Token may be invalid or expired")
                print(f"   Error details: {error_msg}")
            else:
                print(f"❌ Error loading customers: {e}")
            return []
    
    def _normalize_field_name(self, title):
        """
        Normalize column title to field name

        Args:
            title: Column title string

        Returns:
            str: Normalized field name
        """
        # Special handling for "Done?" to keep the "?"
        if title == "Done?":
            return "done?"
        # Standard normalization: lowercase, replace spaces and slashes with underscore
        return title.lower().replace(" ", "_").replace("/", "_")

    def _build_column_map(self, sheet):
        """
        Build comprehensive column mapping

        Args:
            sheet: Smartsheet sheet object

        Returns:
            tuple: (id_map, name_map)
                id_map: {column_id: {id, title, type, field_name}}
                name_map: {field_name: {id, title, type, field_name}}
        """
        id_map = {}
        name_map = {}

        for col in sheet.columns:
            field_name = self._normalize_field_name(col.title)

            col_info = {
                'id': col.id,
                'title': col.title,
                'type': col.type,
                'field_name': field_name
            }

            id_map[col.id] = col_info
            name_map[field_name] = col_info

        return id_map, name_map

    def _extract_all_row_data(self, row, column_map):
        """
        Extract all data from a row (for stage-based processing)

        Args:
            row: Smartsheet row object
            column_map: Pre-built column mapping from _build_column_map()

        Returns:
            dict: All customer data or None if invalid
        """
        customer = {
            "row_id": row.id,
            "row_number": row.row_number
        }

        # Extract all cells using pre-built column map
        for cell in row.cells:
            col_info = column_map.get(cell.column_id)

            if col_info:
                field_name = col_info['field_name']
                col_type = col_info['type']

                # Handle different column types
                if col_type == 'CHECKBOX':
                    value = cell.value if cell.value is not None else False
                elif col_type == 'DATE':
                    # For DATE columns, use cell.value (display_value is often None)
                    value = str(cell.value) if cell.value else ""
                else:
                    value = str(cell.display_value) if cell.display_value else ""

                customer[field_name] = value

        # Only return if has basic required fields for identification
        if customer.get('row_id') and customer.get('row_number'):
            return customer

        return None
    
    def update_customer_fields(self, customer, field_updates, max_retries=3):
        """
        Update multiple fields for a customer with retry logic

        Args:
            customer (dict): Customer record with row_id
            field_updates (dict): Dictionary of field_name: value pairs to update
                Supported fields: ai_call_stage, ai_summary, ai_call_eval,
                                  followup_date, done, etc.
            max_retries (int): Maximum number of retry attempts for 500 errors

        Returns:
            bool: Success status
        """
        import time

        row_id = customer['row_id']
        print(f"📝 Updating row {customer.get('row_number')} with {len(field_updates)} fields...")

        for attempt in range(max_retries):
            try:
                # Get sheet and find column IDs
                sheet = self.smart.Sheets.get_sheet(self.sheet_id)

                # Use existing _build_column_map method (get name_map for field name lookup)
                _, name_map = self._build_column_map(sheet)

                # Prepare cells to update
                cells_to_update = []

                for field_name, value in field_updates.items():
                    col_info = name_map.get(field_name)

                    if not col_info:
                        print(f"   ⚠️  Field '{field_name}' not found in sheet, skipping")
                        continue

                    cell = self.smart.models.Cell()
                    cell.column_id = col_info['id']

                    # Handle different column types
                    if col_info['type'] == 'CHECKBOX':
                        cell.value = bool(value)
                    elif col_info['type'] == 'DATE':
                        # Ensure date is in correct format
                        cell.value = str(value) if value else None
                    else:
                        cell.value = str(value) if value is not None else ""

                    cells_to_update.append(cell)
                    if attempt == 0:  # Only print on first attempt
                        print(f"   • {col_info['title']}: {value}")

                if not cells_to_update:
                    print("   ⚠️  No valid cells to update")
                    return False

                # Create update row
                updated_row = self.smart.models.Row()
                updated_row.id = row_id
                updated_row.cells = cells_to_update

                # Perform update
                result = self.smart.Sheets.update_rows(self.sheet_id, [updated_row])

                if result.result:
                    print(f"   ✅ Successfully updated {len(cells_to_update)} fields")
                    return True
                else:
                    print(f"   ❌ Update failed: {result}")
                    return False

            except Exception as e:
                error_str = str(e)

                # Check if it's a 500 error (server error - retryable)
                if '500' in error_str or 'Internal Server Error' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"   ⚠️  Smartsheet API error (500). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Error updating customer fields after {max_retries} attempts: {e}")
                        return False
                else:
                    # Non-retryable error
                    print(f"❌ Error updating customer fields: {e}")
                    import traceback
                    traceback.print_exc()
                    return False

        return False
