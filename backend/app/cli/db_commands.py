import click
from app.extensions import db

def register_db_commands(app):
    # Register database related CLI commands
    
    @app.cli.group()
    def db_commands():
        """Database related commands."""
        pass

    @db_commands.command('create')
    def create_db():
        """Create the database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @db_commands.command('drop')
    def drop_db():
        """Drop the database tables."""
        db.drop_all()
        click.echo("Database tables dropped.")

    @db_commands.command('reset')
    def reset_db():
        """Reset the database by dropping and creating tables."""
        db.drop_all()
        db.create_all()
        click.echo("Database has been reset.")