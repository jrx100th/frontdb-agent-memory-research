PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS memories (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    step_id INTEGER NOT NULL,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source_ref TEXT,
    file_paths TEXT NOT NULL DEFAULT '[]',
    command TEXT,
    outcome TEXT,
    verification_status TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    token_count INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    file_fingerprints TEXT NOT NULL DEFAULT '[]',
    command_norm TEXT NOT NULL DEFAULT '',
    search_norm TEXT NOT NULL DEFAULT '',
    scientific_key TEXT NOT NULL DEFAULT '',
    supersedes INTEGER,
    invalidated_by INTEGER,
    FOREIGN KEY (supersedes) REFERENCES memories(memory_id),
    FOREIGN KEY (invalidated_by) REFERENCES memories(memory_id)
);
CREATE INDEX IF NOT EXISTS idx_memories_task_step ON memories(task_id, step_id);
CREATE INDEX IF NOT EXISTS idx_memories_invalidated ON memories(task_id, invalidated_by);
CREATE INDEX IF NOT EXISTS idx_memories_fingerprint ON memories(task_id, fingerprint);
CREATE INDEX IF NOT EXISTS idx_memories_task_command ON memories(task_id, command, step_id);
CREATE INDEX IF NOT EXISTS idx_memories_task_command_norm ON memories(task_id, command_norm, step_id);
CREATE INDEX IF NOT EXISTS idx_memories_task_scientific_key ON memories(task_id, scientific_key, step_id, memory_id);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    command,
    source_ref,
    task_id UNINDEXED,
    memory_id UNINDEXED,
    tokenize='unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_norm_fts USING fts5(
    search_norm,
    task_id UNINDEXED,
    memory_id UNINDEXED,
    tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, command, source_ref, task_id, memory_id)
    VALUES (new.memory_id, new.content, coalesce(new.command,''), coalesce(new.source_ref,''), new.task_id, new.memory_id);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, command, source_ref, task_id, memory_id)
    VALUES('delete', old.memory_id, old.content, coalesce(old.command,''), coalesce(old.source_ref,''), old.task_id, old.memory_id);
END;
CREATE TRIGGER IF NOT EXISTS memories_norm_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_norm_fts(rowid, search_norm, task_id, memory_id)
    VALUES (new.memory_id, new.search_norm, new.task_id, new.memory_id);
END;
CREATE TRIGGER IF NOT EXISTS memories_norm_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_norm_fts(memories_norm_fts, rowid, search_norm, task_id, memory_id)
    VALUES('delete', old.memory_id, old.search_norm, old.task_id, old.memory_id);
END;
