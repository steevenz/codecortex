"""
Test file for CodeAuditor comment tag detection.
Contains various comment tags in different formats for testing.
"""

# TODO: This function needs to be implemented
def todo_example():
    pass

# FIXME: This has a bug
def fixme_example():
    # FIXME: Bug on line 12
    x = 1 / 0  # HACK: Temporary workaround
    return x

# XXX: Deprecated code
def xxx_example():
    """
    XXX: This function is deprecated
    Use new_function() instead.
    """
    pass

# WARN: Be careful with this
WARN = "something"

# NOTE: Important information
NOTE = "This is important"

# WIP: Work in progress
def wip_example():
    # WIP: Implementing feature
    pass

# STUB: Placeholder
def stub_example():
    # STUB: Not implemented yet
    raise NotImplementedError()

# REVIEW: Code needs review
def review_example():
    # REVIEW: Check this logic
    pass

# OPTIMIZE: Performance issue
def optimize_example():
    # OPTIMIZE: This loop is slow
    for i in range(1000000):
        pass

# DEPRECATED: Old API
def deprecated_example():
    # DEPRECATED: Use new_api() instead
    pass

# BUG: Known bug
def bug_example():
    # BUG: This crashes on Windows
    pass

# UNDONE: Revert change
def undone_example():
    # UNDONE: Reverted to previous version
    pass