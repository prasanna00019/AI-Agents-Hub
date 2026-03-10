import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:radha@localhost:6739/videonotes')
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute('ALTER TABLE video_notes_cache ADD COLUMN start_time VARCHAR;')
        cur.execute('ALTER TABLE video_notes_cache ADD COLUMN end_time VARCHAR;')
        print('Columns added successfully.')
    except Exception as e:
        print('Could not alter, attempting to drop table so it recreates safely:', e)
        # Rollback the failed transaction first if autocommit wasn't working
        try:
            conn.rollback()
        except:
            pass
        conn.autocommit = True
        cur.execute('DROP TABLE IF EXISTS video_notes_cache CASCADE;')
        print('Table dropped. FastAPI will automatically recreate it.')

    cur.close()
    conn.close()
except Exception as e:
    print('Connection error:', e)
