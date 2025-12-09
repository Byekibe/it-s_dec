"""
CLI commands for the backend application.

Available command groups:
    flask db-commands   Database management (create, drop, reset)
    flask seed          Seed data (permissions, roles, demo)
    flask users         User management (create-owner, create, list, etc.)

Usage examples:
    flask users create-owner              # Bootstrap first owner
    flask seed demo                       # Seed demo data
    flask users list --tenant demo-company
"""


def init_cli(app):
    """Initialize all CLI command groups."""
    from app.cli.db_commands import register_db_commands
    from app.cli.seed_commands import register_seed_commands
    from app.cli.user_commands import register_user_commands

    register_db_commands(app)
    register_seed_commands(app)
    register_user_commands(app)