from typer.testing import CliRunner
from hms_agent.main import app

runner = CliRunner()

def test_app():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "HMS Agent: A multi-agent hotel management system" in result.stdout
