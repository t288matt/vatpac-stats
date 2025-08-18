-- Create Triggers for Controller Summaries Table
-- These triggers automate timestamp updates and other maintenance tasks

-- Trigger to automatically update updated_at timestamp
CREATE TRIGGER update_controller_summaries_updated_at 
    BEFORE UPDATE ON controller_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TRIGGER update_controller_summaries_updated_at ON controller_summaries IS 'Automatically updates updated_at timestamp on row updates';
