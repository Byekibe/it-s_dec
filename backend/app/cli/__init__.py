"""
This module initializes the command-line interface (CLI) for the backend application.
"""

def init_cli(app):
    from app.cli.db_commands import register_db_commands

    register_db_commands(app)