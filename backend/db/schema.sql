-- coursekey database schema
-- run this in supabase sql editor

-- enable uuid extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- table 1: users
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id UUID NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    canvas_api_token TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- table 2: canvas_institutions
-- ============================================
CREATE TABLE canvas_institutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    canvas_domain TEXT NOT NULL UNIQUE,
    canvas_base_url TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- table 3: courses
-- ============================================
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    institution_id UUID REFERENCES canvas_institutions(id) ON DELETE SET NULL,
    canvas_course_id TEXT,
    course_code TEXT NOT NULL,
    course_name TEXT NOT NULL,
    semester TEXT,
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- table 4: course_files (minimized)
-- ============================================
CREATE TABLE course_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_url TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- indexes (for performance)
-- ============================================

-- users indexes
CREATE INDEX idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX idx_users_email ON users(email);

-- institutions indexes
CREATE INDEX idx_canvas_institutions_domain ON canvas_institutions(canvas_domain);

-- courses indexes
CREATE INDEX idx_courses_user_id ON courses(user_id);
CREATE INDEX idx_courses_institution_id ON courses(institution_id);
CREATE INDEX idx_courses_canvas_id ON courses(canvas_course_id);
CREATE INDEX idx_courses_active ON courses(is_active);

-- files indexes
CREATE INDEX idx_course_files_course_id ON course_files(course_id);
CREATE INDEX idx_course_files_type ON course_files(file_type);

-- ============================================
-- comments (for documentation)
-- ============================================

COMMENT ON TABLE users IS 'user profiles linked to supabase auth';
COMMENT ON TABLE canvas_institutions IS 'canvas lms institutions (e.g., universities)';
COMMENT ON TABLE courses IS 'user courses from canvas or manually added';
COMMENT ON TABLE course_files IS 'course files stored in supabase storage';

COMMENT ON COLUMN users.canvas_api_token IS 'encrypted canvas api access token';
COMMENT ON COLUMN courses.is_active IS 'soft delete flag for archived courses';
COMMENT ON COLUMN course_files.storage_path IS 'path in supabase storage bucket (user_id/course_id/filename)';

-- ============================================
-- enable row level security (rls)
-- ============================================

-- enable rls on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE canvas_institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_files ENABLE ROW LEVEL SECURITY;

-- ============================================
-- rls policies
-- ============================================

-- users: can only see/edit their own profile
CREATE POLICY "users can view own profile"
    ON users FOR SELECT
    USING (auth.uid() = auth_user_id);

CREATE POLICY "users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid() = auth_user_id);

CREATE POLICY "users can insert own profile"
    ON users FOR INSERT
    WITH CHECK (auth.uid() = auth_user_id);

-- canvas_institutions: everyone can read (public data)
CREATE POLICY "anyone can view institutions"
    ON canvas_institutions FOR SELECT
    TO authenticated
    USING (true);

-- courses: users can only see their own courses
CREATE POLICY "users can view own courses"
    ON courses FOR SELECT
    USING (user_id IN (
        SELECT id FROM users WHERE auth_user_id = auth.uid()
    ));

CREATE POLICY "users can insert own courses"
    ON courses FOR INSERT
    WITH CHECK (user_id IN (
        SELECT id FROM users WHERE auth_user_id = auth.uid()
    ));

CREATE POLICY "users can update own courses"
    ON courses FOR UPDATE
    USING (user_id IN (
        SELECT id FROM users WHERE auth_user_id = auth.uid()
    ));

CREATE POLICY "users can delete own courses"
    ON courses FOR DELETE
    USING (user_id IN (
        SELECT id FROM users WHERE auth_user_id = auth.uid()
    ));

-- course_files: users can only see files from their courses
CREATE POLICY "users can view own course files"
    ON course_files FOR SELECT
    USING (course_id IN (
        SELECT c.id FROM courses c
        JOIN users u ON c.user_id = u.id
        WHERE u.auth_user_id = auth.uid()
    ));

CREATE POLICY "users can insert files to own courses"
    ON course_files FOR INSERT
    WITH CHECK (course_id IN (
        SELECT c.id FROM courses c
        JOIN users u ON c.user_id = u.id
        WHERE u.auth_user_id = auth.uid()
    ));

CREATE POLICY "users can delete own course files"
    ON course_files FOR DELETE
    USING (course_id IN (
        SELECT c.id FROM courses c
        JOIN users u ON c.user_id = u.id
        WHERE u.auth_user_id = auth.uid()
    ));

-- ============================================
-- service role bypass (for backend operations)
-- ============================================

-- service role can do everything (for your backend)
CREATE POLICY "service role has full access to users"
    ON users FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service role has full access to courses"
    ON courses FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service role has full access to course_files"
    ON course_files FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service role has full access to institutions"
    ON canvas_institutions FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
