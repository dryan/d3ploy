"""
Tests for d3ploy.ui.progress module.
"""

from d3ploy.ui import progress


class TestProgressDisplay:
    """Tests for ProgressDisplay class."""

    def test_init_enabled(self):
        """Test initialization with progress enabled."""
        pd = progress.ProgressDisplay(
            total=100,
            description="Processing",
            disable=False,
            colour="green",
            unit="items",
        )
        assert pd.disable is False
        assert pd.total == 100
        assert pd.description == "Processing"
        assert pd.progress is not None
        assert pd.task_id is None
        assert pd._started is False

    def test_init_disabled(self):
        """Test initialization with progress disabled."""
        pd = progress.ProgressDisplay(total=100, disable=True)
        assert pd.disable is True
        assert not hasattr(pd, "progress")

    def test_context_manager_enabled(self):
        """Test context manager with progress enabled."""
        with progress.ProgressDisplay(total=100, description="Test") as pd:
            assert pd._started is True
            assert pd.task_id is not None

    def test_context_manager_disabled(self):
        """Test context manager with progress disabled."""
        with progress.ProgressDisplay(total=100, disable=True) as pd:
            assert not hasattr(pd, "_started")

    def test_update_enabled(self):
        """Test update method with progress enabled."""
        with progress.ProgressDisplay(total=100, description="Test") as pd:
            pd.update(10)
            # Should not raise an error

    def test_update_disabled(self):
        """Test update method with progress disabled."""
        with progress.ProgressDisplay(total=100, disable=True) as pd:
            pd.update(10)
            # Should not raise an error

    def test_update_without_context_manager(self):
        """Test update method before entering context manager."""
        pd = progress.ProgressDisplay(total=100, description="Test")
        pd.update(10)
        # Should not raise an error (won't do anything)

    def test_set_description_enabled(self):
        """Test set_description method with progress enabled."""
        with progress.ProgressDisplay(total=100, description="Test") as pd:
            pd.set_description("New description")
            # Should not raise an error

    def test_set_description_disabled(self):
        """Test set_description method with progress disabled."""
        with progress.ProgressDisplay(total=100, disable=True) as pd:
            pd.set_description("New description")
            # Should not raise an error

    def test_set_description_without_context_manager(self):
        """Test set_description method before entering context manager."""
        pd = progress.ProgressDisplay(total=100, description="Test")
        pd.set_description("New description")
        # Should not raise an error (won't do anything)

    def test_exit_handler(self):
        """Test __exit__ handles exceptions properly."""
        pd = progress.ProgressDisplay(total=100, description="Test")
        pd.__enter__()
        # Should not raise when exiting
        pd.__exit__(None, None, None)


class TestLiveProgressDisplay:
    """Tests for LiveProgressDisplay class."""

    def test_init_enabled(self):
        """Test initialization with display enabled."""
        lpd = progress.LiveProgressDisplay(title="Test Progress", disable=False)
        assert lpd.disable is False
        assert lpd.title == "Test Progress"
        assert lpd.progress is not None
        assert lpd.tasks == {}
        assert lpd.recent_files == []
        assert lpd.max_recent == 10
        assert lpd._started is False

    def test_init_disabled(self):
        """Test initialization with display disabled."""
        lpd = progress.LiveProgressDisplay(disable=True)
        assert lpd.disable is True
        assert not hasattr(lpd, "progress")

    def test_context_manager_enabled(self):
        """Test context manager with display enabled."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            assert lpd._started is True

    def test_context_manager_disabled(self):
        """Test context manager with display disabled."""
        with progress.LiveProgressDisplay(disable=True) as lpd:
            assert not hasattr(lpd, "_started")

    def test_add_task_enabled(self):
        """Test adding a task with display enabled."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            task_name = lpd.add_task("task1", description="Processing files", total=100)
            assert task_name == "task1"
            assert "task1" in lpd.tasks

    def test_add_task_disabled(self):
        """Test adding a task with display disabled."""
        with progress.LiveProgressDisplay(disable=True) as lpd:
            task_name = lpd.add_task("task1", description="Processing files", total=100)
            assert task_name == "task1"

    def test_update_task_enabled(self):
        """Test updating a task with display enabled."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd.add_task("task1", description="Processing", total=100)
            lpd.update_task("task1", advance=10)
            # Should not raise an error

    def test_update_task_with_description(self):
        """Test updating a task with new description."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd.add_task("task1", description="Processing", total=100)
            lpd.update_task("task1", advance=10, description="Still processing")
            # Should not raise an error

    def test_update_task_disabled(self):
        """Test updating a task with display disabled."""
        with progress.LiveProgressDisplay(disable=True) as lpd:
            lpd.add_task("task1", description="Processing", total=100)
            lpd.update_task("task1", advance=10)
            # Should not raise an error

    def test_update_task_nonexistent(self):
        """Test updating a task that doesn't exist."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd.update_task("nonexistent", advance=10)
            # Should not raise an error (silently ignores)

    def test_add_file_operation_enabled(self):
        """Test adding a file operation with display enabled."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd.add_file_operation(file="test.txt", operation="upload", status="✓")
            assert len(lpd.recent_files) == 1
            assert lpd.recent_files[0]["file"] == "test.txt"
            assert lpd.recent_files[0]["operation"] == "upload"
            assert lpd.recent_files[0]["status"] == "✓"

    def test_add_file_operation_disabled(self):
        """Test adding a file operation with display disabled."""
        with progress.LiveProgressDisplay(disable=True) as lpd:
            lpd.add_file_operation(file="test.txt", operation="upload", status="✓")
            # Should not raise an error

    def test_add_file_operation_max_recent(self):
        """Test that recent files list is capped at max_recent."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            # Add more than max_recent files
            for i in range(15):
                lpd.add_file_operation(
                    file=f"file{i}.txt", operation="upload", status="✓"
                )
            # Should only keep the most recent 10
            assert len(lpd.recent_files) == 10
            # Most recent should be first
            assert lpd.recent_files[0]["file"] == "file14.txt"
            assert lpd.recent_files[9]["file"] == "file5.txt"

    def test_update_display_with_files(self):
        """Test _update_display with recent files."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd.add_file_operation(file="test.txt", operation="upload", status="✓")
            lpd._update_display()
            # Should not raise an error

    def test_update_display_without_files(self):
        """Test _update_display without recent files."""
        with progress.LiveProgressDisplay(title="Test") as lpd:
            lpd._update_display()
            # Should not raise an error

    def test_exit_handler(self):
        """Test __exit__ handles exceptions properly."""
        lpd = progress.LiveProgressDisplay(title="Test")
        lpd.__enter__()
        # Should not raise when exiting
        lpd.__exit__(None, None, None)
