-- Migration script to add team-related columns to existing tables
-- This script should be executed directly in the database to modify existing tables

-- Add team_id column to Nota table if it doesn't exist
ALTER TABLE IF EXISTS notas
ADD COLUMN IF NOT EXISTS team_id UUID;

-- Add team_id column to AgendaEvent table if it doesn't exist
ALTER TABLE IF EXISTS agenda_events
ADD COLUMN IF NOT EXISTS team_id UUID;

-- Add team_id column to Memory table if it doesn't exist
ALTER TABLE IF EXISTS memories
ADD COLUMN IF NOT EXISTS team_id UUID;

-- Add team_id column to ProactiveInsight table if it doesn't exist
ALTER TABLE IF EXISTS proactive_insights
ADD COLUMN IF NOT EXISTS team_id UUID;

-- Create Team table if it doesn't exist
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create TeamMember table if it doesn't exist
CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID NOT NULL,
    account_id UUID NOT NULL,
    role VARCHAR(50),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, account_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Create indexes for better performance on team_id queries
CREATE INDEX IF NOT EXISTS idx_notas_team_id ON notas(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agenda_events_team_id ON agenda_events(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_team_id ON memories(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_proactive_insights_team_id ON proactive_insights(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_account_id ON team_members(account_id);
