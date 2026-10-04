CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS guest_sessions (
	token_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	claimed BOOLEAN NOT NULL,
	PRIMARY KEY (token_hash)
)

;
CREATE INDEX IF NOT EXISTS ix_guest_sessions_expires_at ON guest_sessions (expires_at);

CREATE TABLE IF NOT EXISTS rate_limits (
	key VARCHAR(128) NOT NULL,
	count INTEGER NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (key)
)

;
CREATE INDEX IF NOT EXISTS ix_rate_limits_expires_at ON rate_limits (expires_at);

CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL,
	email VARCHAR(320) NOT NULL,
	password_hash TEXT NOT NULL,
	is_active BOOLEAN DEFAULT 'true' NOT NULL,
	email_verified BOOLEAN DEFAULT 'false' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id)
)

;
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS auth_identities (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	provider VARCHAR(30) NOT NULL,
	subject VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (provider, subject),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS auth_sessions (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	refresh_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (refresh_hash)
)

;
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE IF NOT EXISTS mail_outbox (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	recipient VARCHAR(320) NOT NULL,
	subject VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	status VARCHAR(30) NOT NULL,
	attempts INTEGER NOT NULL,
	lease_until TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS oauth_attempts (
	state_hash VARCHAR(64) NOT NULL,
	nonce VARCHAR(64) NOT NULL,
	verifier VARCHAR(128) NOT NULL,
	handoff_hash VARCHAR(64) NOT NULL,
	code_hash VARCHAR(64),
	user_id UUID,
	link_user_id UUID,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed BOOLEAN NOT NULL,
	PRIMARY KEY (state_hash),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(link_user_id) REFERENCES users (id)
)

;

CREATE TABLE IF NOT EXISTS verification_challenges (
	id UUID NOT NULL,
	user_id UUID NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (token_hash)
)

;
CREATE INDEX IF NOT EXISTS ix_verification_challenges_user_id ON verification_challenges (user_id);

CREATE TABLE IF NOT EXISTS workspaces (
	id UUID NOT NULL,
	name VARCHAR(255) NOT NULL,
	user_id UUID,
	guest_id VARCHAR(64),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_workspace_owner CHECK ((user_id IS NOT NULL) <> (guest_id IS NOT NULL)),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_workspaces_user_id ON workspaces (user_id);
CREATE INDEX IF NOT EXISTS ix_workspaces_guest_id ON workspaces (guest_id);

CREATE TABLE IF NOT EXISTS chat_sessions (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	title VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_chat_sessions_workspace_id ON chat_sessions (workspace_id);

CREATE TABLE IF NOT EXISTS jobs (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	resource_id UUID NOT NULL,
	kind VARCHAR(30) NOT NULL,
	status VARCHAR(30) NOT NULL,
	attempts INTEGER NOT NULL,
	lease_token VARCHAR(64),
	lease_until TIMESTAMP WITH TIME ZONE,
	error TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_jobs_workspace_id ON jobs (workspace_id);
CREATE INDEX IF NOT EXISTS ix_jobs_resource_id ON jobs (resource_id);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status);

CREATE TABLE IF NOT EXISTS stored_objects (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	filename VARCHAR(500) NOT NULL,
	media_type VARCHAR(100) NOT NULL,
	size INTEGER NOT NULL,
	checksum VARCHAR(64) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_stored_objects_workspace_id ON stored_objects (workspace_id);

CREATE TABLE IF NOT EXISTS datasets (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	object_id UUID NOT NULL,
	filename VARCHAR(500) NOT NULL,
	status VARCHAR(30) NOT NULL,
	error TEXT,
	profile JSONB,
	normalized BYTEA,
	version INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	UNIQUE (object_id),
	FOREIGN KEY(object_id) REFERENCES stored_objects (id)
)

;
CREATE INDEX IF NOT EXISTS ix_datasets_workspace_id ON datasets (workspace_id);

CREATE TABLE IF NOT EXISTS documents (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	filename VARCHAR(500) NOT NULL,
	file_type VARCHAR(20) NOT NULL,
	storage_path TEXT,
	object_id UUID,
	error TEXT,
	version INTEGER DEFAULT '1' NOT NULL,
	status VARCHAR(30) NOT NULL,
	summary TEXT,
	metadata_json JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	UNIQUE (object_id),
	FOREIGN KEY(object_id) REFERENCES stored_objects (id)
)

;
CREATE INDEX IF NOT EXISTS ix_documents_workspace_id ON documents (workspace_id);

CREATE TABLE IF NOT EXISTS messages (
	id UUID NOT NULL,
	chat_session_id UUID NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	sources JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_message_role CHECK (role IN ('user','assistant','system')),
	FOREIGN KEY(chat_session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_messages_chat_session_id ON messages (chat_session_id);

CREATE TABLE IF NOT EXISTS object_payloads (
	object_id UUID NOT NULL,
	content BYTEA NOT NULL,
	PRIMARY KEY (object_id),
	FOREIGN KEY(object_id) REFERENCES stored_objects (id) ON DELETE CASCADE
)

;

CREATE TABLE IF NOT EXISTS analysis_results (
	id UUID NOT NULL,
	dataset_id UUID NOT NULL,
	version INTEGER NOT NULL,
	question TEXT,
	plan JSONB NOT NULL,
	result JSONB NOT NULL,
	narrative TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_analysis_results_dataset_id ON analysis_results (dataset_id);

CREATE TABLE IF NOT EXISTS chunks (
	id UUID NOT NULL,
	document_id UUID NOT NULL,
	chunk_index INTEGER NOT NULL,
	page_number INTEGER,
	section_title TEXT,
	location JSONB,
	content TEXT NOT NULL,
	embedding VECTOR(768),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_chunk_index UNIQUE (document_id, chunk_index),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)

;
CREATE INDEX IF NOT EXISTS ix_chunks_document_id ON chunks (document_id);
