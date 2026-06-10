import sqlite3

conn = sqlite3.connect('database/codecortex.db')
cursor = conn.cursor()

# Get all tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()

print("=== Database Field Naming Inconsistencies Analysis ===\n")
print("Standard: snake_case, singular columns\n")

issues = []

for table in tables:
    table_name = table[0]
    
    # Get columns
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    
    col_names = [col[1] for col in columns]
    
    # Check for inconsistencies
    for col_name in col_names:
        # Check for "last_" prefix (should be avoided per standard)
        if col_name.startswith('last_'):
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: 'last_' prefix not standard")
        
        # Check for "synced_at" vs "sync_at" inconsistency
        if col_name.endswith('_synced_at'):
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Should be 'sync_at' not '{col_name}'")
        
        # Check for "cached_at" (should be consistent with sync_at pattern)
        if col_name == 'cached_at':
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Should be 'sync_at' for consistency")
        
        # Check for "checked_at" (should be sync_at pattern)
        if col_name == 'checked_at':
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Should be 'sync_at' for consistency")
        
        # Check for plural names in columns (should be singular per standard)
        if col_name.endswith('s') and not col_name.endswith('ss') and not col_name.endswith('atus'):
            # Skip common exceptions
            if col_name not in ['status', 'class', 'metadata', 'details', 'settings', 'extensions']:
                issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Plural name, should be singular")
        
        # Check for "content_hash" (should be singular)
        if col_name == 'content_hash':
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Should be singular 'content_hashes' -> 'content_hash' OK, but check if array")
        
        # Check for "parent_hashes" (should be singular or use different approach)
        if col_name == 'parent_hashes':
            issues.append(f"Table: {table_name} | Column: {col_name} | Issue: Plural, should be singular 'parent_hash'")

# Check for missing standard columns
print("\n=== Missing Standard Columns ===\n")
for table in tables:
    table_name = table[0]
    
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    
    col_names = [col[1] for col in columns]
    
    missing = []
    if 'id' not in col_names:
        missing.append('id')
    if 'created_at' not in col_names:
        missing.append('created_at')
    if 'updated_at' not in col_names:
        missing.append('updated_at')
    if 'deleted_at' not in col_names:
        missing.append('deleted_at')
    
    if missing:
        print(f"Table: {table_name} | Missing: {', '.join(missing)}")

print("\n=== Field Naming Issues ===\n")
for issue in issues:
    print(issue)

conn.close()
