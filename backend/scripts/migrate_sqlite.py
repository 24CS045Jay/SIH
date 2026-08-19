import sqlite3

def migrate():
    conn = sqlite3.connect('kmrl_portal.db')
    cursor = conn.cursor()

    def add_col(table, col, col_type, default=None):
        cols = [r[1] for r in cursor.execute(f'PRAGMA table_info({table})').fetchall()]
        if col not in cols:
            def_clause = f" DEFAULT '{default}'" if default is not None else ""
            sql = f"ALTER TABLE {table} ADD COLUMN {col} {col_type}{def_clause}"
            print('Executing:', sql)
            cursor.execute(sql)

    add_col('document_versions', 'processing_stage', 'VARCHAR(40)', 'queued')
    add_col('document_versions', 'error_message', 'TEXT')
    add_col('chunks', 'section_number', 'VARCHAR(80)')
    add_col('chunks', 'section_title', 'VARCHAR(300)')
    add_col('chunks', 'subsection', 'VARCHAR(300)')
    add_col('chunks', 'chunk_index', 'INTEGER', '0')
    add_col('chunks', 'token_count', 'INTEGER', '0')
    add_col('chunks', 'ocr_confidence', 'FLOAT')
    add_col('chunks', 'parent_context', 'TEXT')

    conn.commit()
    conn.close()
    print('SQLite migration complete.')

if __name__ == '__main__':
    migrate()
