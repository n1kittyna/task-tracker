import click

from .extensions import db
from .models import Role
from .services.users import create_user


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        click.echo("Таблицы созданы.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):

        create_user(username, email, password, Role.ADMIN.value)
        db.session.commit()
        click.echo(f"Администратор {username} создан.")

    @app.cli.command("test")
    @click.argument("pytest_args", nargs=-1)
    def run_tests(pytest_args):

        import pytest
        raise SystemExit(pytest.main(list(pytest_args) or ["-q"]))